import json

import pytest

from app.models.course import Course
from app.services.course_import_service import CourseImportService


def test_normalize_maps_aliases():
    record = {
        "name": "Intro to Python",
        "summary": "Basics",
        "school": "SampleMOOC",
        "link": "http://x",
        "subject": "编程",
        "level": "beginner",
        "weeks": "4",
        "score": "4.5",
    }

    normalized = CourseImportService.normalize(record)

    assert normalized["title"] == "Intro to Python"
    assert normalized["provider"] == "SampleMOOC"
    assert normalized["category"] == "编程"
    assert normalized["difficulty"] == "beginner"
    assert normalized["duration"] == 4.0
    assert normalized["rating"] == 4.5


def test_normalize_preserves_id():
    normalized = CourseImportService.normalize({"id": 101, "title": "A"})
    assert normalized["id"] == 101


def test_parse_courses_from_list_and_object():
    service = CourseImportService()
    records = [{"title": "A"}, {"title": "B"}]

    assert [c["title"] for c in service.parse_courses(records)] == ["A", "B"]
    assert [c["title"] for c in service.parse_courses({"courses": records})] == [
        "A",
        "B",
    ]


def test_parse_courses_skips_untitled():
    service = CourseImportService()
    assert service.parse_courses([{"description": "no title"}]) == []


def test_parse_courses_rejects_unknown_payload():
    service = CourseImportService()
    with pytest.raises(ValueError):
        service.parse_courses("not-a-list")


def test_import_courses_is_idempotent(app):
    service = CourseImportService()
    source = [
        {
            "title": "Imported Course",
            "description": "d",
            "category": "编程",
            "difficulty": "beginner",
            "duration": 2,
            "rating": 4.0,
        }
    ]

    created, skipped = service.import_courses_from_records(source)
    assert (created, skipped) == (1, 0)
    assert Course.query.filter_by(title="Imported Course").count() == 1

    created, skipped = service.import_courses_from_records(source)
    assert (created, skipped) == (0, 1)
    assert Course.query.filter_by(title="Imported Course").count() == 1


def test_load_local_file(tmp_path):
    path = tmp_path / "courses.json"
    path.write_text(json.dumps([{"title": "File Course"}]), encoding="utf-8")

    service = CourseImportService()
    courses = service.fetch_course_data([str(path)])

    assert courses == [
        {
            "id": None,
            "title": "File Course",
            "description": None,
            "provider": None,
            "url": None,
            "category": None,
            "difficulty": None,
            "duration": None,
            "rating": None,
        }
    ]
