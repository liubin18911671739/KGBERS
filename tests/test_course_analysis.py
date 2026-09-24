from unittest.mock import MagicMock, patch

from app.services.course_analysis_service import CourseAnalysisService


def test_fetch_course_data():
    service = CourseAnalysisService()
    with patch.object(
        service.import_service,
        "fetch_course_data",
        return_value=[
            {"id": 1, "title": "Introduction to Python", "description": "d"},
            {"id": 2, "title": "Data Science", "description": "d"},
        ],
    ):
        course_data = service.fetch_course_data(["http://example.test/courses"])

    assert len(course_data) == 2
    assert course_data[0]["title"] == "Introduction to Python"


def test_fetch_course_data_falls_back_to_sample():
    service = CourseAnalysisService()

    course_data = service.fetch_course_data()

    assert course_data
    assert "title" in course_data[0]


def test_analyze_course_topics():
    service = CourseAnalysisService()
    course_data = [
        {"id": 1, "title": "Introduction to Python", "description": "d"},
        {"id": 2, "title": "Data Science", "description": "d"},
    ]

    with patch.object(
        service, "_perform_topic_modeling", return_value=["Python", "Programming"]
    ):
        course_topics = service.analyze_course_topics(course_data)

    assert course_topics == {
        1: ["Python", "Programming"],
        2: ["Python", "Programming"],
    }


def test_build_course_knowledge_graph():
    service = CourseAnalysisService()
    course_topics = {1: ["Python", "Programming"], 2: ["Data Science", "Python"]}

    with patch("app.services.course_analysis_service.KnowledgeGraph") as mock_kg:
        kg = MagicMock()
        kg.find_concept.return_value = None
        mock_kg.return_value = kg
        service.knowledge_graph = kg

        service.build_course_knowledge_graph(course_topics)

    # find_concept 返回 None(无去重):2 个课程节点 + 4 个主题节点
    assert kg.create_concept.call_count == 6
    # 每门课程 2 个主题关系
    assert kg.create_relationship.call_count == 4


def test_perform_topic_modeling_extracts_keywords():
    service = CourseAnalysisService()

    topics = service._perform_topic_modeling(
        "Python Programming", "Learn python programming and algorithms", top_n=2
    )

    assert "python" in topics
    assert "programming" in topics
