import math

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
)
from flask_login import login_required, current_user
from app.models.recommendation import Recommendation
from app.models.course import Course
from app.models.interaction import EVENT_ANSWER, EVENT_COMPLETE, EVENT_TYPES
from app.services.completion_service import (
    completed_course_ids as get_completed_course_ids,
)
from app.services.recommendation_service import RecommendationService
from app.services.adaptive_recommendation_service import (
    ADAPTIVE_EXPERIMENT,
    AdaptiveRecommendationService,
)
from app.services.concept_graph_service import ConceptGraphService
from app.services.knowledge_tracing_service import KnowledgeTracingService
from app.services.experiment_service import (
    DEFAULT_EXPERIMENT,
    ExperimentService,
    CONTROL,
)

recommendation_bp = Blueprint("recommendation", __name__)


def _current_experiment():
    """实验名通过查询参数/表单字段选择;截断防注入,默认回到默认实验。"""
    name = request.values.get("experiment") or DEFAULT_EXPERIMENT
    name = str(name).strip()[:64]
    return name or DEFAULT_EXPERIMENT


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "correct"}


@recommendation_bp.route("/recommendations/for-you")
@login_required
def for_you():
    experiment_service = ExperimentService()
    experiment = _current_experiment()
    variant = experiment_service.assign(current_user.id, experiment)

    if experiment == ADAPTIVE_EXPERIMENT:
        # 自适应实验:对照组与实验组都展示同样的解释字段,只让排序不同。
        if variant == CONTROL:
            baseline = RecommendationService().recommend_for_user(current_user.id)
            recommendations = AdaptiveRecommendationService().add_explanations(
                current_user.id, baseline
            )
        else:
            recommendations = AdaptiveRecommendationService().recommend_for_user(
                current_user.id
            )
    elif variant == CONTROL:
        excluded = get_completed_course_ids(current_user.id)
        recommendations = [
            {
                "course_id": course.id,
                "title": course.title,
                "category": course.category,
                "difficulty": course.difficulty,
                "score": course.rating if course.rating is not None else 0.0,
            }
            for course in Course.get_top_rated_courses(limit=50)
            if course.id not in excluded
        ][:10]
    else:
        recommendations = RecommendationService().recommend_for_user(current_user.id)

    experiment_service.record_impressions(
        current_user.id,
        [item["course_id"] for item in recommendations],
        variant,
        experiment,
    )
    return render_template(
        "for_you.html",
        recommendations=recommendations,
        variant=variant,
        experiment=experiment,
    )


@recommendation_bp.route("/recommendations/click/<int:course_id>", methods=["POST"])
@login_required
def record_click(course_id):
    """记录推荐点击,用于 CTR 统计。"""
    experiment_service = ExperimentService()
    experiment = _current_experiment()
    variant = experiment_service.assign(current_user.id, experiment)
    experiment_service.record_event(
        current_user.id, course_id, variant, "click", experiment
    )
    return jsonify(success=True)


@recommendation_bp.route("/recommendations/feedback", methods=["POST"])
@login_required
def submit_feedback():
    course_id = int(request.form["course_id"])
    # 评分来自用户输入,限制在 1-5。
    rating = max(1, min(5, int(request.form["rating"])))
    comment = request.form.get("comment")
    # 分组以服务端分配为准,忽略客户端传入的 variant(防止指标被篡改)。
    experiment_service = ExperimentService()
    experiment = _current_experiment()
    variant = experiment_service.assign(current_user.id, experiment)

    experiment_service.record_feedback(
        current_user.id, course_id, rating, comment, variant, experiment
    )
    return redirect(url_for("recommendation.for_you", experiment=experiment))


@recommendation_bp.route("/recommendations/interaction", methods=["POST"])
@login_required
def record_interaction():
    """记录一次答题/完成事件,并立即更新知识追踪状态。"""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form

    try:
        course_id = int(payload.get("course_id"))
    except (TypeError, ValueError):
        return jsonify(message="course_id is required"), 400

    course = Course.query.get(course_id)
    if not course:
        return jsonify(message="Course not found"), 404

    concept = str(payload.get("concept") or "").strip()[:120] or None
    event_type = str(payload.get("event_type") or EVENT_ANSWER).strip().lower()
    if event_type not in EVENT_TYPES:
        return (
            jsonify(message=f"event_type must be one of {EVENT_TYPES}"),
            400,
        )

    correct = _as_bool(payload.get("correct", True))
    response_time = payload.get("response_time")
    if response_time in (None, ""):
        response_time = None
    else:
        try:
            response_time = float(response_time)
            if not math.isfinite(response_time) or response_time < 0:
                response_time = None
        except (TypeError, ValueError):
            response_time = None

    experiment = (
        str(payload.get("experiment") or _current_experiment()).strip()[:64]
        or DEFAULT_EXPERIMENT
    )
    variant = ExperimentService().assign(current_user.id, experiment)

    interaction, state = KnowledgeTracingService().record_interaction(
        current_user.id,
        course.id,
        concept=concept,
        correct=correct,
        response_time=response_time,
        event_type=event_type,
        experiment=experiment,
        variant=variant,
    )
    # 完成事件不改变掌握度,无需重新传播整张概念图。
    propagated = (
        {}
        if event_type == EVENT_COMPLETE
        else ConceptGraphService().propagate_mastery(current_user.id)
    )

    if request.is_json:
        return jsonify(
            success=True,
            interaction_id=interaction.id,
            concept=interaction.concept,
            event_type=event_type,
            experiment=experiment,
            variant=variant,
            mastery=round(state.mastery, 4) if state else None,
            propagated_concepts=len(propagated),
        )

    return redirect(url_for("recommendation.for_you", experiment=_current_experiment()))


@recommendation_bp.route("/recommendations/mastery")
@login_required
def get_mastery():
    """返回当前用户直接观测与图传播后的知识点掌握度。

    默认只返回直接观测概念和课程节点,避免把整张概念图(含 Category/Topic)
    全量返回;``?scope=all`` 可获取完整图。
    """
    scope = (request.args.get("scope") or "course").strip().lower()
    if scope not in ("user", "course", "all"):
        scope = "course"

    tracing = KnowledgeTracingService()
    direct = tracing.mastery_map(current_user.id)
    propagated = ConceptGraphService(tracing_service=tracing).propagate_mastery(
        current_user.id
    )

    if scope == "all":
        visible = None
    elif scope == "user":
        visible = set(direct)
    else:
        visible = set(direct) | {
            key for key in propagated if key.startswith("Course_")
        }

    selected = (
        propagated
        if visible is None
        else {key: value for key, value in propagated.items() if key in visible}
    )
    return jsonify(
        scope=scope,
        direct={key: round(value, 4) for key, value in sorted(direct.items())},
        propagated={
            key: round(value, 4) for key, value in sorted(selected.items())
        },
    )


@recommendation_bp.route("/recommendations/experiments/report")
@login_required
def experiment_report():
    experiment = _current_experiment()
    report = ExperimentService().report(experiment)
    return render_template(
        "experiment_report.html",
        report=report,
        experiment=experiment,
    )


@recommendation_bp.route("/recommendations")
@login_required
def get_user_recommendations():
    user_id = current_user.id
    recommendations = Recommendation.get_user_recommendations(user_id)
    return render_template("recommendation_list.html", recommendations=recommendations)


@recommendation_bp.route("/recommendations/course/<int:course_id>")
@login_required
def get_course_recommendations(course_id):
    recommendations = Recommendation.get_course_recommendations(course_id)
    return render_template("recommendation_list.html", recommendations=recommendations)


@recommendation_bp.route("/recommendations/top")
@login_required
def get_top_recommendations():
    limit = request.args.get("limit", 10, type=int)
    recommendations = Recommendation.get_top_recommendations(limit)
    return render_template("recommendation_list.html", recommendations=recommendations)


@recommendation_bp.route("/recommendations/add", methods=["POST"])
@login_required
def add_recommendation():
    user_id = current_user.id
    payload = request.get_json(silent=True) or {}
    course_id = payload.get("course_id")
    score = float(payload.get("score", 0))

    recommendation = Recommendation.add_recommendation(user_id, course_id, score)
    if not recommendation:
        return jsonify(message="Course not found"), 404

    return jsonify(recommendation_id=recommendation.id), 201


@recommendation_bp.route(
    "/recommendations/<int:recommendation_id>", methods=["PUT", "DELETE"]
)
@login_required
def modify_recommendation(recommendation_id):
    recommendation = Recommendation.query.get(recommendation_id)

    if not recommendation:
        return jsonify(success=False, message="Recommendation not found"), 404

    if recommendation.user_id != current_user.id:
        return jsonify(success=False, message="Forbidden"), 403

    if request.method == "DELETE":
        recommendation.delete()
        return jsonify(success=True)

    score = float((request.get_json(silent=True) or {}).get("score", 0))
    recommendation.score = score
    recommendation.save()
    return jsonify(success=True)
