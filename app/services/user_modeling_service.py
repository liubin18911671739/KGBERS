from app.models.user import User
from app.models.course import Course
from app.models.recommendation import Recommendation


class UserService:
    def get_user_profile(user_id):
        user = User.get_user_by_id(user_id)
        if user:
            profile = {
                "username": user.username,
                "email": user.email,
                "role": user.role,
            }
            return profile
        else:
            return None

    def update_user_profile(user_id, profile_data):
        user = User.get_user_by_id(user_id)
        if user:
            user.username = profile_data.get("username", user.username)
            user.email = profile_data.get("email", user.email)
            user.role = profile_data.get("role", user.role)
            user.save()
            return True
        else:
            return False

    def get_user_course_history(user_id):
        courses = (
            Course.query.join(Recommendation)
            .filter(Recommendation.user_id == user_id)
            .all()
        )
        course_history = [
            {"id": course.id, "title": course.title} for course in courses
        ]
        return course_history

    def get_user_recommendations(user_id, limit=10):
        recommendations = Recommendation.get_user_recommendations(user_id, limit)
        recommended_courses = [
            {"id": rec.course.id, "title": rec.course.title, "score": rec.score}
            for rec in recommendations
        ]
        return recommended_courses

    def add_user_recommendation(user_id, course_id, score):
        recommendation = Recommendation.add_recommendation(user_id, course_id, score)
        if recommendation:
            return {
                "id": recommendation.id,
                "user_id": recommendation.user_id,
                "course_id": recommendation.course_id,
                "score": recommendation.score,
            }
        else:
            return None

    def update_user_recommendation(recommendation_id, score):
        recommendation = Recommendation.query.get(recommendation_id)
        if recommendation:
            recommendation.score = score
            recommendation.save()
            return True
        else:
            return False
