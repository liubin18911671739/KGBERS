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


def test_load_local_csv(tmp_path):
    path = tmp_path / "courses.csv"
    path.write_text(
        "course_title,course_organization,course_rating,course_difficulty\n"
        "Machine Learning,Stanford University,4.7,Intermediate\n",
        encoding="utf-8",
    )

    service = CourseImportService()
    courses = service.fetch_course_data([str(path)])

    assert len(courses) == 1
    assert courses[0]["title"] == "Machine Learning"
    assert courses[0]["provider"] == "Stanford University"
    assert courses[0]["rating"] == 4.7
    assert courses[0]["difficulty"] == "intermediate"


def test_parse_csv_semicolon_delimited():
    """Class Central 等真实数据集使用分号分隔,自动识别。"""
    text = (
        "Course Id;Course Name;Provider;Institutions;Parent.Subject;Url;Length;;\n"
        "301;Introduction to AI;Udacity;Stanford University;Computer Science;"
        "https://www.ai-class.com/;10;;\n"
    )

    rows = CourseImportService._parse_csv(text)
    normalized = CourseImportService.normalize(rows[0])

    assert len(rows) == 1
    assert normalized["title"] == "Introduction to AI"
    assert normalized["provider"] == "Udacity"
    assert normalized["category"] == "Computer Science"
    assert normalized["url"] == "https://www.ai-class.com/"
    assert normalized["duration"] == 10.0


def test_normalize_coursera_dataset_columns():
    """真实 Coursera 数据集列名映射(无 description/url 时留空)。"""
    record = {
        "course_title": "AI For Everyone",
        "course_organization": "deeplearning.ai",
        "course_rating": "4.8",
        "course_difficulty": "Beginner",
        "course_students_enrolled": "350k",
    }

    normalized = CourseImportService.normalize(record)

    assert normalized["title"] == "AI For Everyone"
    assert normalized["provider"] == "deeplearning.ai"
    assert normalized["rating"] == 4.8
    assert normalized["difficulty"] == "beginner"
    assert normalized["description"] is None


def test_normalize_classcentral_dataset_columns():
    """Class Central 分号 CSV(解析后)的列名映射。"""
    record = {
        "Course Id": "301",
        "Course Name": "Introduction to Artificial Intelligence",
        "Provider": "Udacity",
        "Institutions": "Stanford University",
        "Parent.Subject": "Computer Science",
        "Url": "https://www.ai-class.com/",
        "Length": "10",
    }

    normalized = CourseImportService.normalize(record)

    assert normalized["title"] == "Introduction to Artificial Intelligence"
    assert normalized["provider"] == "Udacity"
    assert normalized["category"] == "Computer Science"
    assert normalized["url"] == "https://www.ai-class.com/"
    assert normalized["duration"] == 10.0
    assert normalized["id"] == "301"


def test_fetch_course_data_isolates_failing_source(tmp_path):
    """单个源失败不受影响,仍有其他源课程返回。"""
    good = tmp_path / "good.json"
    good.write_text(json.dumps([{"title": "Good Course"}]), encoding="utf-8")

    service = CourseImportService()
    courses = service.fetch_course_data(
        [str(tmp_path / "missing.json"), str(good)]
    )

    assert [c["title"] for c in courses] == ["Good Course"]


def test_fetch_course_data_falls_back_to_sample_when_all_fail():
    """全部 URL 失败时回退内置样例,而非返回空列表。"""
    from unittest.mock import patch

    import requests as requests_lib

    service = CourseImportService()
    with patch.object(
        requests_lib,
        "get",
        side_effect=requests_lib.RequestException("boom"),
    ):
        courses = service.fetch_course_data(["https://example.com/courses.json"])

    assert courses  # 内置样例可用
    assert any(c["title"] for c in courses)


def test_fetch_course_data_all_formats_fail_returns_empty_list(tmp_path):
    """无样例可用时保持 list 约定(不抛出),由调用方决定降级。"""
    from unittest.mock import patch

    import requests as requests_lib

    import app.services.course_import_service as import_mod

    service = CourseImportService()
    with patch.object(
        requests_lib, "get", side_effect=requests_lib.RequestException("boom")
    ), patch.object(import_mod, "SAMPLE_PATH", str(tmp_path / "nope.json")):
        courses = service.fetch_course_data(["https://example.com/courses.json"])

    assert courses == []


def test_remote_csv_source(tmp_path):
    """URL 指向 CSV 时按 CSV 解析(模拟真实 GitHub raw 数据源)。"""
    from unittest.mock import patch

    class FakeResponse:
        status_code = 200
        text = (
            "course_title,course_organization,course_rating,course_difficulty\n"
            "Algorithms,Princeton University,4.8,Intermediate\n"
        )

        headers = {"Content-Type": "text/csv"}

        def raise_for_status(self):
            pass

        def json(self):  # pragma: no cover - CSV 路径不应走到这里
            raise AssertionError("CSV source must not be parsed as JSON")

    service = CourseImportService()
    with patch("requests.get", return_value=FakeResponse()):
        courses = service.fetch_course_data(["https://example.com/courses.csv"])

    assert len(courses) == 1
    assert courses[0]["title"] == "Algorithms"
    assert courses[0]["provider"] == "Princeton University"
