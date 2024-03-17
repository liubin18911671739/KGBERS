from app.models.recommendation import Recommendation
from app.models.course import Course
from app.models.user import User


class RecommendationService:
    def get_user_recommendations(user_id, limit=10):
        recommendations = (
            Recommendation.query.filter_by(user_id=user_id)
            .order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        return recommendations

    def get_course_recommendations(course_id, limit=10):
        recommendations = (
            Recommendation.query.filter_by(course_id=course_id)
            .order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        return recommendations

    def get_top_recommendations(limit=10):
        recommendations = (
            Recommendation.query.order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        return recommendations

    def add_recommendation(user_id, course_id, score):
        user = User.query.get(user_id)
        course = Course.query.get(course_id)

        if user and course:
            recommendation = Recommendation(user=user, course=course, score=score)
            recommendation.save()
            return recommendation
        else:
            return None

    def update_recommendation(recommendation_id, score):
        recommendation = Recommendation.query.get(recommendation_id)

        if recommendation:
            recommendation.score = score
            recommendation.save()
            return recommendation
        else:
            return None

    def delete_recommendation(recommendation_id):
        recommendation = Recommendation.query.get(recommendation_id)

        if recommendation:
            recommendation.delete()
            return True
        else:
            return False
