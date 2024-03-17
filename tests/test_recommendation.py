import unittest
from unittest.mock import MagicMock, patch
from app.services.recommendation_service import RecommendationService


class TestRecommendation(unittest.TestCase):

    def setUp(self):
        self.recommendation_service = RecommendationService()

    def test_get_user_recommendations(self):
        user_id = 1
        limit = 2
        expected_recommendations = [
            {"id": 1, "title": "Python for Beginners", "score": 4.5},
            {"id": 2, "title": "Advanced Python Programming", "score": 4.2},
        ]

        with patch(
            "app.services.recommendation_service.Recommendation"
        ) as mock_recommendation:
            mock_recommendation.query.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
                MagicMock(
                    course=MagicMock(id=1, title="Python for Beginners"), score=4.5
                ),
                MagicMock(
                    course=MagicMock(id=2, title="Advanced Python Programming"),
                    score=4.2,
                ),
            ]

            recommendations = self.recommendation_service.get_user_recommendations(
                user_id, limit
            )

            self.assertEqual(recommendations, expected_recommendations)
            mock_recommendation.query.filter_by.assert_called_once_with(user_id=user_id)
            mock_recommendation.query.filter_by.return_value.order_by.assert_called_once_with(
                mock_recommendation.score.desc()
            )
            mock_recommendation.query.filter_by.return_value.order_by.return_value.limit.assert_called_once_with(
                limit
            )

    def test_get_course_recommendations(self):
        course_id = 1
        limit = 2
        expected_recommendations = [
            {"id": 1, "title": "Data Science Fundamentals", "score": 4.7},
            {"id": 2, "title": "Machine Learning with Python", "score": 4.5},
        ]

        with patch(
            "app.services.recommendation_service.Recommendation"
        ) as mock_recommendation:
            mock_recommendation.query.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
                MagicMock(
                    course=MagicMock(id=1, title="Data Science Fundamentals"), score=4.7
                ),
                MagicMock(
                    course=MagicMock(id=2, title="Machine Learning with Python"),
                    score=4.5,
                ),
            ]

            recommendations = self.recommendation_service.get_course_recommendations(
                course_id, limit
            )

            self.assertEqual(recommendations, expected_recommendations)
            mock_recommendation.query.filter_by.assert_called_once_with(
                course_id=course_id
            )
            mock_recommendation.query.filter_by.return_value.order_by.assert_called_once_with(
                mock_recommendation.score.desc()
            )
            mock_recommendation.query.filter_by.return_value.order_by.return_value.limit.assert_called_once_with(
                limit
            )

    def test_get_top_recommendations(self):
        limit = 2
        expected_recommendations = [
            {"id": 1, "title": "Python for Data Analysis", "score": 4.9},
            {"id": 2, "title": "Web Development with Django", "score": 4.8},
        ]

        with patch(
            "app.services.recommendation_service.Recommendation"
        ) as mock_recommendation:
            mock_recommendation.query.order_by.return_value.limit.return_value.all.return_value = [
                MagicMock(
                    course=MagicMock(id=1, title="Python for Data Analysis"), score=4.9
                ),
                MagicMock(
                    course=MagicMock(id=2, title="Web Development with Django"),
                    score=4.8,
                ),
            ]

            recommendations = self.recommendation_service.get_top_recommendations(limit)

            self.assertEqual(recommendations, expected_recommendations)
            mock_recommendation.query.order_by.assert_called_once_with(
                mock_recommendation.score.desc()
            )
            mock_recommendation.query.order_by.return_value.limit.assert_called_once_with(
                limit
            )

    def test_add_recommendation(self):
        user_id = 1
        course_id = 1
        score = 4.5

        with patch("app.services.recommendation_service.User") as mock_user:
            with patch("app.services.recommendation_service.Course") as mock_course:
                with patch(
                    "app.services.recommendation_service.Recommendation"
                ) as mock_recommendation:
                    mock_user_instance = MagicMock()
                    mock_course_instance = MagicMock()
                    mock_recommendation_instance = MagicMock(
                        id=1, user_id=user_id, course_id=course_id, score=score
                    )
                    mock_user.query.get.return_value = mock_user_instance
                    mock_course.query.get.return_value = mock_course_instance
                    mock_recommendation.return_value = mock_recommendation_instance

                    recommendation = self.recommendation_service.add_recommendation(
                        user_id, course_id, score
                    )

                    self.assertEqual(recommendation["id"], 1)
                    self.assertEqual(recommendation["user_id"], user_id)
                    self.assertEqual(recommendation["course_id"], course_id)
                    self.assertEqual(recommendation["score"], score)
                    mock_user.query.get.assert_called_once_with(user_id)
                    mock_course.query.get.assert_called_once_with(course_id)
                    mock_recommendation.assert_called_once_with(
                        user=mock_user_instance,
                        course=mock_course_instance,
                        score=score,
                    )
                    mock_recommendation_instance.save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
