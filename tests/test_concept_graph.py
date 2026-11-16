from app.models.course import Course
from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.concept_graph_service import ConceptGraphService
from app.services.knowledge_tracing_service import (
    KnowledgeTracingService,
    course_concept,
)


def _course(title, category="编程", difficulty="beginner"):
    return Course.add_course(title, "d", "p", "u", category, difficulty, 1, 4.0)


def test_graph_propagates_mastery_to_related_course(app):
    user = User.add_user("u", "u@example.com", "pw")
    python = _course("Python", "编程")
    algorithms = _course("Algo", "编程", "intermediate")
    algorithms.add_prerequisite(python)

    KnowledgeTracingService().record_interaction(
        user.id, python.id, correct=True
    )
    mastery = ConceptGraphService().propagate_mastery(user.id)

    assert mastery[course_concept(python.id)] > 0.3
    # 同类别 + 先修关系让算法课程获得正向迁移,但不应超过直接观测课程。
    assert 0.0 < mastery[course_concept(algorithms.id)] < mastery[
        course_concept(python.id)
    ]


def test_course_readiness_uses_prerequisite_completion(app):
    user = User.add_user("u", "u@example.com", "pw")
    python = _course("Python", "编程")
    algorithms = _course("Algo", "编程", "intermediate")
    algorithms.add_prerequisite(python)

    without_completion = ConceptGraphService().course_readiness(
        user.id, algorithms.id, completed_course_ids=set()
    )
    with_completion = ConceptGraphService().course_readiness(
        user.id, algorithms.id, completed_course_ids={python.id}
    )

    assert without_completion["prerequisite_readiness"] == 0.0
    assert with_completion["prerequisite_readiness"] == 1.0
    assert 0.0 <= with_completion["mastery"] <= 1.0
    assert 0.0 <= with_completion["mastery_gap"] <= 1.0


def test_graph_without_neo4j_still_has_course_and_category_nodes(app):
    user = User.add_user("u", "u@example.com", "pw")
    course = _course("Python", "编程")
    Recommendation.add_recommendation(user.id, course.id, 5.0)

    mastery = ConceptGraphService().propagate_mastery(user.id)

    assert course_concept(course.id) in mastery
    assert "Category_编程" in mastery


def test_title_tokens_transfer_across_categories(app):
    user = User.add_user("u", "u@example.com", "pw")
    python = _course("Python 编程入门", "编程")
    data = _course("Python 数据分析", "数据科学")

    KnowledgeTracingService().record_interaction(
        user.id, python.id, correct=True
    )
    mastery = ConceptGraphService().propagate_mastery(user.id)

    # 不同类别,但标题共享 "python",形成跨课程概念链接。
    assert mastery[course_concept(data.id)] > 0.0
