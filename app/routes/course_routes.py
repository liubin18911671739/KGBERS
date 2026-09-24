from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import current_user
from app.models.course import Course
from app.services.learning_path_service import LearningPathService

course_bp = Blueprint("course", __name__)

PER_PAGE = 10


def _filter_options():
    categories = [
        row[0]
        for row in Course.query.with_entities(Course.category).distinct().all()
        if row[0]
    ]
    difficulties = [
        row[0]
        for row in Course.query.with_entities(Course.difficulty).distinct().all()
        if row[0]
    ]
    return categories, difficulties


@course_bp.route("/courses")
def get_all_courses():
    page = request.args.get("page", 1, type=int)
    pagination = Course.query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    categories, difficulties = _filter_options()
    return render_template(
        "course_list.html",
        courses=pagination.items,
        pagination=pagination,
        categories=categories,
        difficulties=difficulties,
    )


@course_bp.route("/courses/<int:course_id>")
def get_course(course_id):
    course = Course.get_course_by_id(course_id)
    if course:
        return render_template("course_detail.html", course=course)
    else:
        return jsonify(message="Course not found"), 404


@course_bp.route("/courses/<int:course_id>/path")
def learning_path(course_id):
    course = Course.get_course_by_id(course_id)
    if not course:
        return jsonify(message="Course not found"), 404

    service = LearningPathService()
    if current_user.is_authenticated:
        path = service.path_for_user(current_user.id, course_id)
    else:
        path = service.build_path(course_id)

    return render_template("learning_path.html", course=course, path=path)


@course_bp.route("/courses/add", methods=["GET", "POST"])
def add_course():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        provider = request.form["provider"]
        url = request.form["url"]
        category = request.form["category"]
        difficulty = request.form["difficulty"]
        duration = request.form.get("duration", type=float)
        rating = request.form.get("rating", type=float)

        course = Course.add_course(
            title, description, provider, url, category, difficulty, duration, rating
        )

        return redirect(url_for("course.get_course", course_id=course.id))

    return render_template("add_course.html")


@course_bp.route("/courses/search")
def search_courses():
    keyword = request.args.get("keyword", "")
    courses = Course.search_courses(keyword)
    categories, difficulties = _filter_options()
    return render_template(
        "course_list.html",
        courses=courses,
        categories=categories,
        difficulties=difficulties,
    )


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

    categories, difficulties = _filter_options()
    return render_template(
        "course_list.html",
        courses=courses,
        categories=categories,
        difficulties=difficulties,
    )


@course_bp.route("/courses/top_rated")
def get_top_rated_courses():
    limit = int(request.args.get("limit", 10))
    courses = Course.get_top_rated_courses(limit)
    categories, difficulties = _filter_options()
    return render_template(
        "course_list.html",
        courses=courses,
        categories=categories,
        difficulties=difficulties,
    )
