from app.models.course import Course
from app.models.user import User
from app.services.adaptive_recommendation_service import (
    ADAPTIVE_EXPERIMENT,
    AdaptiveRecommendationService,
)
from app.services.knowledge_tracing_service import KnowledgeTracingService


def _course(title, category="编程", difficulty="beginner"):
    return Course.add_course(title, "d", "p", "u", category, difficulty, 1, 4.0)


class _FixedBaseline:
    """固定 baseline 分数,用于隔离自适应信号的影响。"""

    def __init__(self, course_ids):
        self.course_ids = course_ids

    def recommend_for_user(self, user_id, limit=10):
        return [
            {"course_id": course_id, "score": 0.5}
            for course_id in self.course_ids
        ]


def test_adaptive_recommendation_returns_explanations(app):
    user = User.add_user("u", "u@example.com", "pw")
    course = _course("Python")
    KnowledgeTracingService().record_interaction(user.id, course.id, correct=True)

    results = AdaptiveRecommendationService().recommend_for_user(user.id)

    assert results
    item = results[0]
    assert item["course_id"] == course.id
    assert 0.0 <= item["score"] <= 1.0
    assert "baseline_score" in item
    assert "adaptive_score" in item
    assert "mastery" in item
    assert item["reason"]


def test_adaptive_signal_prefers_lower_mastery_course(app):
    user = User.add_user("u", "u@example.com", "pw")
    observed = _course("Observed", "编程")
    related = _course("Related", "编程")
    unrelated = _course("Unrelated", "艺术")
    KnowledgeTracingService().record_interaction(
        user.id, observed.id, correct=True
    )

    service = AdaptiveRecommendationService(
        baseline_service=_FixedBaseline([related.id, unrelated.id])
    )
    results = service.recommend_for_user(user.id)
    ids = [item["course_id"] for item in results]

    # 已观测课程的同类别课程掌握度更高,缺口更小;跨类别课程缺口更大。
    assert ids.index(unrelated.id) < ids.index(related.id)


def test_adaptive_recommendation_unknown_user(app):
    assert AdaptiveRecommendationService().recommend_for_user(9999) == []


def test_adaptive_experiment_constant():
    assert ADAPTIVE_EXPERIMENT == "adaptive_kt"
