from app.models.course import Course
from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.user_modeling_service import UserModelingService, UserService


def test_user_modeling_service_alias():
    assert UserModelingService is UserService


def test_get_user_profile(app):
    user = User.add_user("john_doe", "john@example.com", "pw")

    profile = UserService().get_user_profile(user.id)

    assert profile == {
        "username": "john_doe",
        "email": "john@example.com",
        "role": "student",
    }


def test_get_user_profile_missing(app):
    assert UserService().get_user_profile(9999) is None


def test_update_user_profile(app):
    user = User.add_user("john", "john@example.com", "pw")

    ok = UserService().update_user_profile(
        user.id, {"username": "john_smith", "email": "js@example.com"}
    )

    assert ok is True
    updated = User.get_user_by_id(user.id)
    assert updated is not None
    assert updated.username == "john_smith"
    assert updated.email == "js@example.com"


def test_update_user_profile_missing(app):
    assert UserService().update_user_profile(9999, {"username": "x"}) is False


def test_get_user_course_history(app):
    user = User.add_user("u", "u@example.com", "pw")
    c1 = Course.add_course("C1", "d", "p", "u", "x", "beginner", 1, 4.0)
    c2 = Course.add_course("C2", "d", "p", "u", "x", "beginner", 1, 4.0)
    Recommendation.add_recommendation(user.id, c1.id, 5.0)
    Recommendation.add_recommendation(user.id, c2.id, 4.0)

    history = UserService().get_user_course_history(user.id)

    assert {item["title"] for item in history} == {"C1", "C2"}


def test_get_user_recommendations(app):
    user = User.add_user("u", "u@example.com", "pw")
    c1 = Course.add_course("C1", "d", "p", "u", "x", "beginner", 1, 4.0)
    Recommendation.add_recommendation(user.id, c1.id, 4.5)

    recommendations = UserService().get_user_recommendations(user.id)

    assert recommendations == [{"id": c1.id, "title": "C1", "score": 4.5}]
