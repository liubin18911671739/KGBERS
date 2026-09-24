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
from app.services.recommendation_service import RecommendationService
from app.services.experiment_service import (
    ExperimentService,
    CONTROL,
    DEFAULT_EXPERIMENT,
)

recommendation_bp = Blueprint("recommendation", __name__)


@recommendation_bp.route("/recommendations/for-you")
@login_required
def for_you():
    experiment_service = ExperimentService()
    variant = experiment_service.assign(current_user.id)

    if variant == CONTROL:
        recommendations = [
            {
                "course_id": course.id,
                "title": course.title,
                "category": course.category,
                "difficulty": course.difficulty,
                "score": course.rating if course.rating is not None else 0.0,
            }
            for course in Course.get_top_rated_courses(limit=10)
        ]
    else:
        recommendations = RecommendationService().recommend_for_user(current_user.id)

    experiment_service.record_impressions(
        current_user.id, [item["course_id"] for item in recommendations], variant
    )
    return render_template(
        "for_you.html",
        recommendations=recommendations,
        variant=variant,
    )


@recommendation_bp.route("/recommendations/click/<int:course_id>", methods=["POST"])
@login_required
def record_click(course_id):
    """记录推荐点击,用于 CTR 统计。"""
    variant = ExperimentService().assign(current_user.id)
    ExperimentService().record_event(current_user.id, course_id, variant, "click")
    return jsonify(success=True)


@recommendation_bp.route("/recommendations/feedback", methods=["POST"])
@login_required
def submit_feedback():
    course_id = int(request.form["course_id"])
    # 评分来自用户输入,限制在 1-5。
    rating = max(1, min(5, int(request.form["rating"])))
    comment = request.form.get("comment")
    # 分组以服务端分配为准,忽略客户端传入的 variant(防止指标被篡改)。
    variant = ExperimentService().assign(current_user.id)

    ExperimentService().record_feedback(
        current_user.id, course_id, rating, comment, variant
    )
    return redirect(url_for("recommendation.for_you"))


@recommendation_bp.route("/recommendations/experiments/report")
@login_required
def experiment_report():
    report = ExperimentService().report()
    return render_template(
        "experiment_report.html",
        report=report,
        experiment=DEFAULT_EXPERIMENT,
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
