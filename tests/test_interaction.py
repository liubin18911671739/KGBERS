from app.models.course import Course
from app.models.experiment import ExperimentAssignment, RecommendationEvent
from app.models.interaction import Interaction, KnowledgeState
from app.models.user import User
from app.services.adaptive_recommendation_service import ADAPTIVE_EXPERIMENT
from app.services.experiment_service import ExperimentService


def _course(title="C"):
    return Course.add_course(title, "d", "p", "u", "编程", "beginner", 1, 4.0)


def test_interaction_endpoint_records_json(app, client):
    user = User.add_user("u", "u@example.com", "pw")
    course = _course()
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.post(
        "/recommendation/recommendations/interaction",
        json=dict(
            course_id=course.id,
            correct=True,
            response_time=12.5,
            event_type="answer",
        ),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["event_type"] == "answer"
    assert payload["mastery"] > 0.3
    assert Interaction.query.filter_by(user_id=user.id).count() == 1
    assert KnowledgeState.query.filter_by(user_id=user.id).count() == 1


def test_completion_event_does_not_inflate_mastery(app, client):
    user = User.add_user("u", "u@example.com", "pw")
    completed = _course("Completed")
    other = _course("Other")
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.post(
        "/recommendation/recommendations/interaction",
        json=dict(course_id=completed.id, event_type="complete"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["event_type"] == "complete"
    assert payload["mastery"] is None
    assert Interaction.query.one().event_type == "complete"
    assert Interaction.query.one().correct is False
    # 完成不等于答对,不应创建/抬高掌握度。
    assert KnowledgeState.query.count() == 0

    from app.services.learning_path_service import LearningPathService
    from app.services.recommendation_service import RecommendationService

    recommended_ids = [
        item["course_id"]
        for item in RecommendationService().recommend_for_user(user.id)
    ]
    assert completed.id not in recommended_ids
    assert other.id in recommended_ids

    path = LearningPathService().path_for_user(user.id, completed.id)
    assert path[0]["course_id"] == completed.id
    assert path[0]["completed"] is True


def test_interaction_endpoint_rejects_invalid_event_type(app, client):
    User.add_user("u", "u@example.com", "pw")
    course = _course()
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.post(
        "/recommendation/recommendations/interaction",
        json=dict(course_id=course.id, event_type="unknown"),
    )

    assert response.status_code == 400
    assert Interaction.query.count() == 0


def test_interaction_endpoint_normalizes_input(app, client):
    User.add_user("u", "u@example.com", "pw")
    course = _course()
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.post(
        "/recommendation/recommendations/interaction",
        json=dict(
            course_id=course.id,
            concept=123,
            correct=True,
            response_time=-5,
        ),
    )

    assert response.status_code == 200
    interaction = Interaction.query.one()
    assert interaction.concept == "123"
    assert interaction.response_time is None


def test_interaction_endpoint_rejects_non_object_json(app, client):
    User.add_user("u", "u@example.com", "pw")
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.post(
        "/recommendation/recommendations/interaction",
        json=[1, 2, 3],
    )

    assert response.status_code == 400
    assert Interaction.query.count() == 0


def test_interaction_endpoint_records_form_and_redirects(app, client):
    User.add_user("u", "u@example.com", "pw")
    course = _course()
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.post(
        "/recommendation/recommendations/interaction",
        data=dict(course_id=course.id, correct="1"),
    )

    assert response.status_code == 302
    assert Interaction.query.count() == 1


def test_interaction_endpoint_rejects_unknown_course(app, client):
    User.add_user("u", "u@example.com", "pw")
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.post(
        "/recommendation/recommendations/interaction",
        json=dict(course_id=9999, correct=True),
    )

    assert response.status_code == 404
    assert Interaction.query.count() == 0


def test_mastery_endpoint_returns_direct_and_propagated(app, client):
    user = User.add_user("u", "u@example.com", "pw")
    course = _course()
    client.post("/user/login", data=dict(username="u", password="pw"))
    client.post(
        "/recommendation/recommendations/interaction",
        json=dict(course_id=course.id, correct=True),
    )

    response = client.get("/recommendation/recommendations/mastery")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["direct"]
    assert payload["propagated"]
    # 默认只返回课程节点/直接概念,不返回 Category_/Topic_ 内部节点。
    assert all(
        key.startswith("Course_") for key in payload["propagated"]
    )

    full = client.get("/recommendation/recommendations/mastery?scope=all")
    assert full.status_code == 200
    assert any(
        key.startswith("Category_") for key in full.get_json()["propagated"]
    )


def test_adaptive_experiment_isolated_from_default(app, client):
    user = User.add_user("u", "u@example.com", "pw")
    _course()
    client.post("/user/login", data=dict(username="u", password="pw"))

    response = client.get(
        f"/recommendation/recommendations/for-you?experiment={ADAPTIVE_EXPERIMENT}"
    )

    assert response.status_code == 200
    assert ExperimentAssignment.query.filter_by(
        user_id=user.id, experiment=ADAPTIVE_EXPERIMENT
    ).count() == 1
    assert (
        RecommendationEvent.query.filter_by(
            user_id=user.id, experiment=ADAPTIVE_EXPERIMENT
        ).count()
        > 0
    )
    # 默认实验不产生额外分组。
    assert ExperimentAssignment.query.filter_by(
        user_id=user.id, experiment="recommendation"
    ).count() == 0


def test_adaptive_experiment_control_uses_baseline(app, client, monkeypatch):
    User.add_user("u", "u@example.com", "pw")
    _course()
    client.post("/user/login", data=dict(username="u", password="pw"))
    monkeypatch.setattr(
        ExperimentService,
        "assign",
        lambda self, user_id, experiment="recommendation": "control",
    )

    response = client.get(
        f"/recommendation/recommendations/for-you?experiment={ADAPTIVE_EXPERIMENT}"
    )

    assert response.status_code == 200
    assert b"control" in response.data
    # 对照组也展示与 treatment 相同的解释字段。
    assert "推荐理由" in response.data.decode("utf-8")


def test_adaptive_experiment_treatment_renders_reason(app, client, monkeypatch):
    user = User.add_user("u", "u@example.com", "pw")
    course = _course()
    client.post("/user/login", data=dict(username="u", password="pw"))
    client.post(
        "/recommendation/recommendations/interaction",
        json=dict(course_id=course.id, correct=True),
    )
    monkeypatch.setattr(
        ExperimentService,
        "assign",
        lambda self, user_id, experiment="recommendation": "treatment",
    )

    response = client.get(
        f"/recommendation/recommendations/for-you?experiment={ADAPTIVE_EXPERIMENT}"
    )

    assert response.status_code == 200
    assert "推荐理由" in response.data.decode("utf-8")
