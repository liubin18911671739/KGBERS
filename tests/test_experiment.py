from app.models.course import Course
from app.models.experiment import (
    ExperimentAssignment,
    Feedback,
    RecommendationEvent,
)
from app.models.user import User
from app.services.experiment_service import (
    ExperimentService,
    CONTROL,
    DEFAULT_EXPERIMENT,
    TREATMENT,
)


def test_assign_is_deterministic(app):
    user = User.add_user("u", "u@example.com", "pw")
    service = ExperimentService()

    first = service.assign(user.id)
    second = service.assign(user.id)

    assert first == second
    assert first in (CONTROL, TREATMENT)


def test_assign_creates_single_assignment(app):
    user = User.add_user("u", "u@example.com", "pw")
    service = ExperimentService()

    service.assign(user.id)
    service.assign(user.id)

    assert ExperimentAssignment.query.filter_by(user_id=user.id).count() == 1


def test_record_feedback_and_event(app):
    user = User.add_user("u", "u@example.com", "pw")
    course = Course.add_course("C", "d", "p", "u", "x", "beginner", 1, 4.0)
    service = ExperimentService()

    service.record_feedback(user.id, course.id, 5, "great", TREATMENT)
    service.record_event(user.id, course.id, TREATMENT, "impression")
    service.record_event(user.id, course.id, TREATMENT, "click")

    assert Feedback.query.filter_by(variant=TREATMENT).count() == 1
    assert RecommendationEvent.query.filter_by(variant=TREATMENT).count() == 2


def test_report_metrics(app):
    user = User.add_user("u", "u@example.com", "pw")
    course = Course.add_course("C", "d", "p", "u", "x", "beginner", 1, 4.0)
    service = ExperimentService()
    variant = service.assign(user.id)

    service.record_feedback(user.id, course.id, 4, None, variant)
    service.record_event(user.id, course.id, variant, "impression")
    service.record_event(user.id, course.id, variant, "impression")
    service.record_event(user.id, course.id, variant, "click")

    report = service.report()

    assert set(report.keys()) == {CONTROL, TREATMENT}
    assert report[variant]["users"] == 1
    assert report[variant]["avg_rating"] == 4.0
    assert report[variant]["impressions"] == 2
    assert report[variant]["clicks"] == 1
    assert report[variant]["ctr"] == 0.5


def test_record_impressions_dedupes(app):
    user = User.add_user("u", "u@example.com", "pw")
    a = Course.add_course("A", "d", "p", "u", "x", "beginner", 1, 4.0)
    b = Course.add_course("B", "d", "p", "u", "x", "beginner", 1, 4.0)
    service = ExperimentService()

    service.record_impressions(user.id, [a.id, b.id], TREATMENT)
    service.record_impressions(user.id, [a.id, b.id], TREATMENT)

    assert RecommendationEvent.query.filter_by(
        user_id=user.id, event_type="impression"
    ).count() == 2


def test_for_you_and_feedback_routes(app, client):
    user = User.add_user("u", "u@example.com", "pw")
    course = Course.add_course("C", "d", "p", "u", "x", "beginner", 1, 4.0)
    client.post("/user/login", data=dict(username="u", password="pw"))

    assert client.get("/recommendation/recommendations/for-you").status_code == 200

    response = client.post(
        "/recommendation/recommendations/feedback",
        data=dict(course_id=course.id, rating=5, variant=TREATMENT),
    )

    assert response.status_code == 302
    feedback = Feedback.query.one()
    # 分组以服务端分配为准,不受表单传入值影响
    assert feedback.variant == ExperimentService().assign(user.id)


def test_feedback_clamps_rating(app, client):
    User.add_user("u", "u@example.com", "pw")
    course = Course.add_course("C", "d", "p", "u", "x", "beginner", 1, 4.0)
    client.post("/user/login", data=dict(username="u", password="pw"))

    client.post(
        "/recommendation/recommendations/feedback",
        data=dict(course_id=course.id, rating=99),
    )

    assert Feedback.query.one().rating == 5


def test_click_endpoint_records_event(app, client):
    user = User.add_user("u", "u@example.com", "pw")
    course = Course.add_course("C", "d", "p", "u", "x", "beginner", 1, 4.0)
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.post(f"/recommendation/recommendations/click/{course.id}")

    assert response.status_code == 200
    assert RecommendationEvent.query.filter_by(
        user_id=user.id, event_type="click"
    ).count() == 1


def test_assign_is_per_experiment(app):
    user = User.add_user("u", "u@example.com", "pw")
    service = ExperimentService()

    default_variant = service.assign(user.id, DEFAULT_EXPERIMENT)
    other_variant = service.assign(user.id, "new_ranking")

    assert ExperimentAssignment.query.filter_by(user_id=user.id).count() == 2
    assert default_variant in (CONTROL, TREATMENT)
    assert other_variant in (CONTROL, TREATMENT)


def test_report_isolates_experiments(app):
    user = User.add_user("u", "u@example.com", "pw")
    course = Course.add_course("C", "d", "p", "u", "x", "beginner", 1, 4.0)
    service = ExperimentService()

    default_variant = service.assign(user.id, DEFAULT_EXPERIMENT)
    other_variant = service.assign(user.id, "new_ranking")

    service.record_feedback(
        user.id, course.id, 5, None, default_variant, DEFAULT_EXPERIMENT
    )
    service.record_feedback(user.id, course.id, 1, None, other_variant, "new_ranking")
    service.record_event(
        user.id, course.id, default_variant, "impression", DEFAULT_EXPERIMENT
    )
    service.record_event(
        user.id, course.id, other_variant, "impression", "new_ranking"
    )

    default_report = service.report(DEFAULT_EXPERIMENT)
    other_report = service.report("new_ranking")

    assert default_report[default_variant]["feedback_count"] == 1
    assert default_report[default_variant]["avg_rating"] == 5.0
    assert other_report[other_variant]["feedback_count"] == 1
    assert other_report[other_variant]["avg_rating"] == 1.0
    # 另一个实验的数据不应串扰到默认实验。
    for variant in (CONTROL, TREATMENT):
        if variant != default_variant:
            assert default_report[variant]["feedback_count"] == 0


def test_impressions_dedupe_within_experiment(app):
    user = User.add_user("u", "u@example.com", "pw")
    course = Course.add_course("C", "d", "p", "u", "x", "beginner", 1, 4.0)
    service = ExperimentService()

    service.record_impressions(user.id, [course.id], TREATMENT, DEFAULT_EXPERIMENT)
    service.record_impressions(user.id, [course.id], TREATMENT, DEFAULT_EXPERIMENT)
    # 不同实验的曝光互不干扰,各自落一条。
    service.record_impressions(user.id, [course.id], TREATMENT, "new_ranking")

    assert (
        RecommendationEvent.query.filter_by(
            user_id=user.id,
            experiment=DEFAULT_EXPERIMENT,
            event_type="impression",
        ).count()
        == 1
    )
    assert (
        RecommendationEvent.query.filter_by(
            user_id=user.id, experiment="new_ranking", event_type="impression"
        ).count()
        == 1
    )


def test_for_you_carries_experiment_dimension(app, client):
    user = User.add_user("u", "u@example.com", "pw")
    course = Course.add_course("C", "d", "p", "u", "x", "beginner", 1, 4.0)
    client.post("/user/login", data=dict(username="u", password="pw"))

    assert (
        client.get(
            "/recommendation/recommendations/for-you?experiment=new_ranking"
        ).status_code
        == 200
    )
    assert (
        RecommendationEvent.query.filter_by(experiment="new_ranking").count() > 0
    )
    # 未带参数的访问仍归属默认实验。
    assert client.get("/recommendation/recommendations/for-you").status_code == 200
    assert (
        RecommendationEvent.query.filter_by(
            experiment=DEFAULT_EXPERIMENT
        ).count()
        > 0
    )


def test_feedback_post_follows_experiment_query_param(app, client):
    user = User.add_user("u", "u@example.com", "pw")
    course = Course.add_course("C", "d", "p", "u", "x", "beginner", 1, 4.0)
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.post(
        "/recommendation/recommendations/feedback?experiment=new_ranking",
        data=dict(course_id=course.id, rating=4),
    )

    assert response.status_code == 302
    feedback = Feedback.query.one()
    assert feedback.experiment == "new_ranking"
    assert feedback.variant == ExperimentService().assign(user.id, "new_ranking")


def test_report_page_renders_selected_experiment(app, client):
    User.add_user("u", "u@example.com", "pw")
    Course.add_course("C", "d", "p", "u", "x", "beginner", 1, 4.0)
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.get(
        "/recommendation/recommendations/experiments/report?experiment=new_ranking"
    )

    assert response.status_code == 200
    assert b"new_ranking" in response.data
