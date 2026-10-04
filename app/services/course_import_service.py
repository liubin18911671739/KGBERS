import csv
import io
import json
import logging
import os

import requests

from app.models.course import Course


logger = logging.getLogger(__name__)

SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "samples",
    "mooc_courses.json",
)

# 真实 MOOC 数据集常见列名别名(Coursera/edX/Class Central 爬取集等)。
FIELD_ALIASES = {
    "id": ("id", "course_id", "uid", "Course Id"),
    "title": ("title", "name", "course_title", "Course Name", "course name"),
    "description": ("description", "summary", "short_description"),
    "provider": (
        "provider",
        "course_organization",
        "institution",
        "school",
        "org",
    ),
    "url": ("url", "link", "course_url", "Url"),
    "category": (
        "category",
        "subject",
        "topic",
        "Parent.Subject",
        "Child.Subject",
        "subject_name",
    ),
    "difficulty": (
        "difficulty",
        "level",
        "course_difficulty",
    ),
    "duration": ("duration", "length", "weeks", "Length"),
    "rating": ("rating", "score", "course_rating"),
}

DEFAULT_TIMEOUT = 15


class CourseImportService:
    def fetch_course_data(self, sources=None, timeout=DEFAULT_TIMEOUT):
        """
        从配置的数据源读取课程原始数据。

        source 可以是 URL(JSON/CSV) 或本地文件路径;未配置时回退到内置样例。
        单个源失败仅记录日志并跳过,不影响其他源;全部失败或解析为空时
        回退到内置样例,保证调用方始终拿到可用数据。
        """
        sources = sources or self.default_sources()
        if not sources:
            sources = [SAMPLE_PATH]

        courses = []
        for source in sources:
            try:
                payload = self._load(source, timeout)
            except Exception:
                # _load 已记录具体失败原因;单个源失败不中断整体导入。
                continue
            courses.extend(self.parse_courses(payload))

        if not courses:
            logger.warning("all course sources failed, falling back to bundled sample")
            try:
                payload = self._load(SAMPLE_PATH, timeout)
                courses.extend(self.parse_courses(payload))
            except Exception:
                logger.exception("bundled sample fallback failed as well")
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

    def import_courses(self, sources=None, timeout=DEFAULT_TIMEOUT):
        """抓取并写入数据库(按标题去重),返回 (created, skipped)。"""
        return self.import_courses_from_records(
            self.fetch_course_data(sources, timeout)
        )

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
    def _load(source, timeout=DEFAULT_TIMEOUT):
        """加载单个数据源;URL 支持 JSON 与 CSV,失败时抛出异常并记录日志。"""
        try:
            if source.startswith("http://") or source.startswith("https://"):
                response = requests.get(source, timeout=timeout)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                if "csv" in content_type or source.lower().endswith(".csv"):
                    return CourseImportService._parse_csv(response.text)
                return response.json()
            with open(source, "r", encoding="utf-8-sig") as handle:
                text = handle.read()
            if source.lower().endswith(".csv"):
                return CourseImportService._parse_csv(text)
            return json.loads(text)
        except Exception:
            logger.warning("course import failed for source %r", source, exc_info=True)
            raise

    @staticmethod
    def _parse_csv(text):
        """解析 CSV(含 BOM/多余列),返回标准课程记录列表。

        自动识别逗号/分号/制表符分隔(真实数据集两者皆有)。
        """
        text = text.lstrip("\ufeff")
        header = text.splitlines()[0] if text else ""
        delimiter = ";"
        if header.count(",") > header.count(";"):
            delimiter = "," if "\t" not in header else "\t"
        elif header.count("\t") > header.count(";"):
            delimiter = "\t"
        reader = csv.DictReader(io.StringIO(text), restval="", delimiter=delimiter)
        records = []
        for row in reader:
            # 过滤全空的尾部列/空行。
            cleaned = {
                (k or "").strip(): v for k, v in row.items() if k is not None
            }
            if any(str(v or "").strip() for v in cleaned.values()):
                records.append(cleaned)
        return records

    @staticmethod
    def normalize(record):
        # 真实数据集列名大小写不一(Class Central 用 'Course Name'),
        # 以不区分大小写的方式做别名匹配。
        lowered = {
            (key or "").strip().lower(): value for key, value in record.items()
        }

        def pick(field):
            for alias in FIELD_ALIASES[field]:
                value = lowered.get(alias.lower())
                if value not in (None, ""):
                    return value
            return None

        duration = pick("duration")
        rating = pick("rating")

        category = pick("category")
        difficulty = CourseImportService._normalize_difficulty(pick("difficulty"))
        # rating 可能形如 "4.7"(Coursera 数据集),转换失败则留空。
        return {
            "id": pick("id"),
            "title": pick("title"),
            "description": pick("description"),
            "provider": pick("provider"),
            "url": pick("url"),
            "category": CourseImportService._clean_category(category),
            "difficulty": difficulty,
            "duration": CourseImportService._to_float(duration),
            "rating": CourseImportService._to_float(rating),
        }

    @staticmethod
    def _normalize_difficulty(value):
        """统一难度为 beginner/intermediate/advanced。"""
        if not value:
            return None
        text = str(value).strip().lower()
        if text in ("beginner", "easy", "intro", "introductory"):
            return "beginner"
        if text in ("intermediate", "mixed", "medium"):
            return "intermediate"
        if text in ("advanced", "expert", "hard"):
            return "advanced"
        return text

    @staticmethod
    def _clean_category(value):
        """数据集常用 'Parent.Subject' 等列名;取点号后的可读部分。"""
        if not value:
            return None
        text = str(value).strip()
        return text.split(".", 1)[-1].strip() or None

    @staticmethod
    def _to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
