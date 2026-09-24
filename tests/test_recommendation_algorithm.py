from app.models.course import Course
from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.recommendation_service import RecommendationService


def test_recommend_for_user_excludes_rated_and_prefers_category(app):
    user = User.add_user("u", "u@example.com", "pw")
    liked = Course.add_course("Python", "d", "p", "u", "编程", "beginner", 10, 4.0)
    same_category = Course.add_course("Algo", "d", "p", "u", "编程", "beginner", 10, 4.0)
    other_category = Course.add_course("Art", "d", "p", "u", "艺术", "beginner", 10, 4.0)
    Recommendation.add_recommendation(user.id, liked.id, 5.0)

    results = RecommendationService().recommend_for_user(user.id)
    ids = [item["course_id"] for item in results]

    assert liked.id not in ids
    assert ids.index(same_category.id) < ids.index(other_category.id)


def test_recommend_for_user_quality_signal(app):
    user = User.add_user("u", "u@example.com", "pw")
    peer = User.add_user("peer", "peer@example.com", "pw")
    popular = Course.add_course("Popular", "d", "p", "u", "编程", "beginner", 10, 4.0)
    quiet = Course.add_course("Quiet", "d", "p", "u", "编程", "beginner", 10, 4.0)
    Recommendation.add_recommendation(user.id, Course.add_course("Seed", "d", "p", "u", "编程", "beginner", 1, 4.0).id, 4.0)
    Recommendation.add_recommendation(peer.id, popular.id, 5.0)

    results = RecommendationService().recommend_for_user(user.id)
    ids = [item["course_id"] for item in results]

    assert ids.index(popular.id) < ids.index(quiet.id)


def test_recommend_for_user_cold_start(app):
    user = User.add_user("u", "u@example.com", "pw")
    Course.add_course("Only", "d", "p", "u", "x", "beginner", 1, 4.0)

    results = RecommendationService().recommend_for_user(user.id)

    assert len(results) == 1


def test_recommend_for_user_unknown_user(app):
    assert RecommendationService().recommend_for_user(12345) == []
