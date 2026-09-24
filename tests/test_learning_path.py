from app.models.course import Course
from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.learning_path_service import LearningPathService


def _course(title, difficulty="beginner", rating=4.0, category="编程"):
    return Course.add_course(title, "d", "p", "u", category, difficulty, 1.0, rating)


def test_build_path_orders_prerequisites_first(app):
    a = _course("A", "beginner")
    b = _course("B", "intermediate")
    c = _course("C", "advanced")
    b.add_prerequisite(a)
    c.add_prerequisite(b)

    path = LearningPathService().build_path(c.id)

    assert [step["course_id"] for step in path] == [a.id, b.id, c.id]


def test_build_path_handles_diamond(app):
    a = _course("A")
    b = _course("B", "intermediate")
    c = _course("C", "intermediate")
    d = _course("D", "advanced")
    b.add_prerequisite(a)
    c.add_prerequisite(a)
    d.add_prerequisite(b)
    d.add_prerequisite(c)

    ids = [step["course_id"] for step in LearningPathService().build_path(d.id)]

    assert len(ids) == 4
    assert ids.index(a.id) < ids.index(b.id) < ids.index(d.id)
    assert ids.index(a.id) < ids.index(c.id) < ids.index(d.id)


def test_build_path_without_prerequisites(app):
    solo = _course("Solo")

    path = LearningPathService().build_path(solo.id)

    assert [step["course_id"] for step in path] == [solo.id]


def test_build_path_unknown_course(app):
    assert LearningPathService().build_path(9999) == []


def test_build_path_handles_cycle(app):
    a = _course("A")
    b = _course("B")
    a.add_prerequisite(b)
    b.add_prerequisite(a)

    path = LearningPathService().build_path(a.id)

    assert {step["course_id"] for step in path} == {a.id, b.id}


def test_path_for_user_marks_completed(app):
    a = _course("A")
    b = _course("B")
    b.add_prerequisite(a)
    user = User.add_user("u", "u@example.com", "pw")
    Recommendation.add_recommendation(user.id, a.id, 5.0)

    path = LearningPathService().path_for_user(user.id, b.id)
    completed = {step["course_id"]: step["completed"] for step in path}

    assert completed[a.id] is True
    assert completed[b.id] is False
