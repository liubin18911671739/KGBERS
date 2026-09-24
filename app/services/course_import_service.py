import json
import os

import requests

from app.models.course import Course


SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "samples",
    "mooc_courses.json",
)

FIELD_ALIASES = {
    "id": ("id", "course_id", "uid"),
    "title": ("title", "name", "course_title"),
    "description": ("description", "summary", "short_description"),
    "provider": ("provider", "institution", "school", "org"),
    "url": ("url", "link", "course_url"),
    "category": ("category", "subject", "topic"),
    "difficulty": ("difficulty", "level"),
    "duration": ("duration", "length", "weeks"),
    "rating": ("rating", "score"),
}


class CourseImportService:
    def fetch_course_data(self, sources=None):
        """
        从配置的数据源读取课程原始数据。

        source 可以是 URL(JSON) 或本地文件路径;未配置时回退到内置样例。
        解析失败时抛出 ValueError,调用方可选择降级。
        """
        sources = sources or self.default_sources()
        if not sources:
            sources = [SAMPLE_PATH]

        courses = []
        for source in sources:
            payload = self._load(source)
            courses.extend(self.parse_courses(payload))
        return courses

    def parse_courses(self, payload):
        """将 JSON(对象或列表)映射为标准化课程字典列表。"""
        if isinstance(payload, dict):
            records = payload.get("courses") or payload.get("results") or []
        elif isinstance(payload, list):
            records = payload
        else:
            raise ValueError("unsupported course payload type")

        normalized = [self.normalize(record) for record in records]
        return [record for record in normalized if record["title"]]

    def import_courses(self, sources=None):
        """抓取并写入数据库(按标题去重),返回 (created, skipped)。"""
        return self.import_courses_from_records(self.fetch_course_data(sources))

    def import_courses_from_records(self, records):
        created = skipped = 0
        for record in records:
            record = self.normalize(record)
            if not record["title"]:
                continue
            if Course.query.filter_by(title=record["title"]).first():
                skipped += 1
                continue
            Course.add_course(
                record["title"],
                record["description"],
                record["provider"],
                record["url"],
                record["category"],
                record["difficulty"],
                record["duration"],
                record["rating"],
            )
            created += 1
        return created, skipped

    @staticmethod
    def default_sources():
        from flask import current_app, has_app_context

        if not has_app_context():
            return []
        urls = current_app.config.get("COURSE_DATA_URLS") or []
        return [url for url in urls if url]

    @staticmethod
    def _load(source):
        if source.startswith("http://") or source.startswith("https://"):
            response = requests.get(source, timeout=15)
            response.raise_for_status()
            return response.json()
        with open(source, "r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def normalize(record):
        def pick(field):
            for alias in FIELD_ALIASES[field]:
                value = record.get(alias)
                if value not in (None, ""):
                    return value
            return None

        duration = pick("duration")
        rating = pick("rating")
        return {
            "id": pick("id"),
            "title": pick("title"),
            "description": pick("description"),
            "provider": pick("provider"),
            "url": pick("url"),
            "category": pick("category"),
            "difficulty": pick("difficulty"),
            "duration": CourseImportService._to_float(duration),
            "rating": CourseImportService._to_float(rating),
        }

    @staticmethod
    def _to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
