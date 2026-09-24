from flask import Blueprint, render_template
from app.models.course import Course
from app.services.recommendation_service import RecommendationService

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    recommendation_service = RecommendationService()

    top_rated_courses = Course.get_top_rated_courses(limit=5)
    recommended_courses = recommendation_service.get_top_recommendations(limit=5)

    return render_template(
        "index.html",
        top_rated_courses=top_rated_courses,
        recommended_courses=recommended_courses,
    )


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/contact")
def contact():
    return render_template("contact.html")
