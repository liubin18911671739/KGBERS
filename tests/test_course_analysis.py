import unittest
from unittest.mock import MagicMock, patch
from app.services.course_analysis_service import CourseAnalysisService


class TestCourseAnalysis(unittest.TestCase):

    def setUp(self):
        self.course_analysis_service = CourseAnalysisService()

    def test_fetch_course_data(self):
        with patch("app.services.course_analysis_service.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "courses": [
                    {
                        "id": 1,
                        "title": "Introduction to Python",
                        "description": "Learn the basics of Python programming",
                        "url": "https://example.com/python",
                    },
                    {
                        "id": 2,
                        "title": "Data Science with Python",
                        "description": "Explore data science concepts using Python",
                        "url": "https://example.com/data-science",
                    },
                ]
            }
            mock_get.return_value = mock_response

            course_data = self.course_analysis_service.fetch_course_data()

            self.assertEqual(len(course_data), 2)
            self.assertEqual(course_data[0]["title"], "Introduction to Python")
            self.assertEqual(course_data[1]["url"], "https://example.com/data-science")

    def test_analyze_course_topics(self):
        course_data = [
            {
                "id": 1,
                "title": "Introduction to Python",
                "description": "Learn the basics of Python programming",
            },
            {
                "id": 2,
                "title": "Data Science with Python",
                "description": "Explore data science concepts using Python",
            },
        ]

        with patch(
            "app.services.course_analysis_service.CourseAnalysisService._perform_topic_modeling"
        ) as mock_topic_modeling:
            mock_topic_modeling.return_value = {
                1: ["Python", "Programming"],
                2: ["Data Science", "Python"],
            }

            course_topics = self.course_analysis_service.analyze_course_topics(
                course_data
            )

            self.assertEqual(len(course_topics), 2)
            self.assertEqual(course_topics[1], ["Python", "Programming"])
            self.assertEqual(course_topics[2], ["Data Science", "Python"])

    def test_build_course_knowledge_graph(self):
        course_topics = {1: ["Python", "Programming"], 2: ["Data Science", "Python"]}

        with patch(
            "app.services.course_analysis_service.KnowledgeGraph"
        ) as mock_knowledge_graph:
            mock_graph = MagicMock()
            mock_knowledge_graph.return_value = mock_graph

            self.course_analysis_service.build_course_knowledge_graph(course_topics)

            self.assertEqual(mock_knowledge_graph.call_count, 1)
            self.assertEqual(mock_graph.create_concept.call_count, 3)
            self.assertEqual(mock_graph.create_relationship.call_count, 2)


if __name__ == "__main__":
    unittest.main()
