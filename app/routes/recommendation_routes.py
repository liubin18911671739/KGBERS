from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.recommendation import Recommendation

recommendation_bp = Blueprint("recommendation", __name__)


@recommendation_bp.route("/recommendations")
@login_required
def get_user_recommendations():
    user_id = current_user.id
    recommendations = Recommendation.get_user_recommendations(user_id)
    return render_template("recommendation_list.html", recommendations=recommendations)


@recommendation_bp.route("/recommendations/course/<int:course_id>")
def get_course_recommendations(course_id):
    recommendations = Recommendation.get_course_recommendations(course_id)
    return render_template("recommendation_list.html", recommendations=recommendations)


@recommendation_bp.route("/recommendations/top")
def get_top_recommendations():
    limit = int(request.args.get("limit", 10))
    recommendations = Recommendation.get_top_recommendations(limit)
    return render_template("recommendation_list.html", recommendations=recommendations)


@recommendation_bp.route("/recommendations/add", methods=["POST"])
@login_required
def add_recommendation():
    user_id = current_user.id
    course_id = request.json["course_id"]
    score = float(request.json["score"])

    recommendation = Recommendation.add_recommendation(user_id, course_id, score)

    return jsonify(recommendation_id=recommendation.id), 201
