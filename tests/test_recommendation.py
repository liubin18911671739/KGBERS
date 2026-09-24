from app.models.course import Course
from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.recommendation_service import RecommendationService


def _fixtures():
    user = User.add_user("alice", "alice@example.com", "pw")
    c1 = Course.add_course("C1", "d", "p", "u", "编程", "beginner", 10, 4.5)
    c2 = Course.add_course("C2", "d", "p", "u", "编程", "advanced", 10, 4.0)
    c3 = Course.add_course("C3", "d", "p", "u", "艺术", "beginner", 10, 3.0)
    return user, c1, c2, c3


def test_get_user_recommendations_orders_by_score(app):
    user, c1, c2, _ = _fixtures()
    Recommendation.add_recommendation(user.id, c1.id, 3.0)
    Recommendation.add_recommendation(user.id, c2.id, 5.0)

    recommendations = RecommendationService().get_user_recommendations(user.id)

    assert [r.course_id for r in recommendations] == [c2.id, c1.id]
    assert all(isinstance(r, Recommendation) for r in recommendations)


def test_get_course_recommendations(app):
    user, c1, _, _ = _fixtures()
    other = User.add_user("bob", "bob@example.com", "pw")
    Recommendation.add_recommendation(user.id, c1.id, 3.0)
    Recommendation.add_recommendation(other.id, c1.id, 5.0)

    recommendations = RecommendationService().get_course_recommendations(c1.id)

    assert [r.user_id for r in recommendations] == [other.id, user.id]


def test_get_top_recommendations(app):
    user, c1, c2, c3 = _fixtures()
    Recommendation.add_recommendation(user.id, c1.id, 1.0)
    Recommendation.add_recommendation(user.id, c2.id, 5.0)
    Recommendation.add_recommendation(user.id, c3.id, 3.0)

    recommendations = RecommendationService().get_top_recommendations(limit=2)

    assert [r.course_id for r in recommendations] == [c2.id, c3.id]


def test_add_recommendation_returns_model(app):
    user, c1, _, _ = _fixtures()

    recommendation = RecommendationService().add_recommendation(user.id, c1.id, 4.2)

    assert isinstance(recommendation, Recommendation)
    assert recommendation.user_id == user.id
    assert recommendation.course_id == c1.id
    assert recommendation.score == 4.2


def test_add_recommendation_missing_user_returns_none(app):
    _, c1, _, _ = _fixtures()

    assert RecommendationService().add_recommendation(9999, c1.id, 1.0) is None


def test_update_and_delete_recommendation(app):
    user, c1, _, _ = _fixtures()
    recommendation = RecommendationService().add_recommendation(user.id, c1.id, 2.0)
    assert recommendation is not None

    updated = RecommendationService().update_recommendation(recommendation.id, 4.0)
    assert updated is not None
    assert updated.score == 4.0

    assert RecommendationService().delete_recommendation(recommendation.id) is True
    assert RecommendationService().delete_recommendation(recommendation.id) is False
