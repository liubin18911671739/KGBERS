import unittest
from unittest.mock import MagicMock, patch
from app.services.user_modeling_service import UserModelingService


class TestUserModeling(unittest.TestCase):

    def setUp(self):
        self.user_modeling_service = UserModelingService()

    def test_get_user_profile(self):
        user_id = 1
        expected_profile = {
            "username": "john_doe",
            "email": "john@example.com",
            "role": "student",
        }

        with patch("app.services.user_modeling_service.User") as mock_user:
            mock_user.get_user_by_id.return_value = MagicMock(
                username="john_doe", email="john@example.com", role="student"
            )

            profile = self.user_modeling_service.get_user_profile(user_id)

            self.assertEqual(profile, expected_profile)
            mock_user.get_user_by_id.assert_called_once_with(user_id)

    def test_update_user_profile(self):
        user_id = 1
        profile_data = {"username": "john_smith", "email": "john.smith@example.com"}

        with patch("app.services.user_modeling_service.User") as mock_user:
            mock_user_instance = MagicMock()
            mock_user.get_user_by_id.return_value = mock_user_instance

            result = self.user_modeling_service.update_user_profile(
                user_id, profile_data
            )

            self.assertTrue(result)
            mock_user.get_user_by_id.assert_called_once_with(user_id)
            self.assertEqual(mock_user_instance.username, "john_smith")
            self.assertEqual(mock_user_instance.email, "john.smith@example.com")
            mock_user_instance.save.assert_called_once()

    def test_get_user_course_history(self):
        user_id = 1
        expected_course_history = [
            {"id": 1, "title": "Introduction to Python"},
            {"id": 2, "title": "Data Science with Python"},
        ]

        with patch("app.services.user_modeling_service.Course") as mock_course:
            with patch(
                "app.services.user_modeling_service.Recommendation"
            ) as mock_recommendation:
                mock_course.query.join.return_value.filter.return_value.all.return_value = [
                    MagicMock(id=1, title="Introduction to Python"),
                    MagicMock(id=2, title="Data Science with Python"),
                ]

                course_history = self.user_modeling_service.get_user_course_history(
                    user_id
                )

                self.assertEqual(course_history, expected_course_history)
                mock_course.query.join.assert_called_once_with(mock_recommendation)
                mock_course.query.join.return_value.filter.assert_called_once_with(
                    mock_recommendation.user_id == user_id
                )

    def test_get_user_recommendations(self):
        user_id = 1
        limit = 2
        expected_recommendations = [
            {"id": 1, "title": "Python for Beginners", "score": 4.5},
            {"id": 2, "title": "Advanced Python Programming", "score": 4.2},
        ]

        with patch(
            "app.services.user_modeling_service.Recommendation"
        ) as mock_recommendation:
            mock_recommendation.get_user_recommendations.return_value = [
                MagicMock(
                    course=MagicMock(id=1, title="Python for Beginners"), score=4.5
                ),
                MagicMock(
                    course=MagicMock(id=2, title="Advanced Python Programming"),
                    score=4.2,
                ),
            ]

            recommendations = self.user_modeling_service.get_user_recommendations(
                user_id, limit
            )

            self.assertEqual(recommendations, expected_recommendations)
            mock_recommendation.get_user_recommendations.assert_called_once_with(
                user_id, limit
            )


if __name__ == "__main__":
    unittest.main()
