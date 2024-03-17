from flask import Blueprint, render_template, request, jsonify
from app.models.course import Course

course_bp = Blueprint("course", __name__)


@course_bp.route("/courses")
def get_all_courses():
    courses = Course.query.all()
    return render_template("course_list.html", courses=courses)


@course_bp.route("/courses/<int:course_id>")
def get_course(course_id):
    course = Course.get_course_by_id(course_id)
    if course:
        return render_template("course_detail.html", course=course)
    else:
        return jsonify(message="Course not found"), 404


@course_bp.route("/courses/add", methods=["GET", "POST"])
def add_course():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        provider = request.form["provider"]
        url = request.form["url"]
        category = request.form["category"]
        difficulty = request.form["difficulty"]
        duration = float(request.form["duration"])
        rating = float(request.form["rating"])

        course = Course.add_course(
            title, description, provider, url, category, difficulty, duration, rating
        )

        return jsonify(course_id=course.id), 201

    return render_template("add_course.html")


@course_bp.route("/courses/search")
def search_courses():
    keyword = request.args.get("keyword", "")
    courses = Course.search_courses(keyword)
    return render_template("course_list.html", courses=courses)


@course_bp.route("/courses/filter")
def filter_courses():
    category = request.args.get("category", "")
    difficulty = request.args.get("difficulty", "")

    if category and difficulty:
        courses = Course.query.filter_by(category=category, difficulty=difficulty).all()
    elif category:
        courses = Course.get_courses_by_category(category)
    elif difficulty:
        courses = Course.get_courses_by_difficulty(difficulty)
    else:
        courses = Course.query.all()

    return render_template("course_list.html", courses=courses)


@course_bp.route("/courses/top_rated")
def get_top_rated_courses():
    limit = int(request.args.get("limit", 10))
    courses = Course.get_top_rated_courses(limit)
    return render_template("course_list.html", courses=courses)
