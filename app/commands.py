import click

from app import db
from app.models.course import Course
from app.models.user import User
from app.models.recommendation import Recommendation


SAMPLE_COURSES = [
    {
        "title": "Python 编程入门",
        "description": "Python 基础语法、数据结构与编程思维。",
        "provider": "MOOC",
        "url": "https://example.com/python",
        "category": "编程",
        "difficulty": "beginner",
        "duration": 20.0,
        "rating": 4.6,
    },
    {
        "title": "数据结构与算法",
        "description": "线性表、树、图与常见算法设计。",
        "provider": "MOOC",
        "url": "https://example.com/algorithms",
        "category": "编程",
        "difficulty": "intermediate",
        "duration": 36.0,
        "rating": 4.7,
    },
    {
        "title": "机器学习基础",
        "description": "监督学习、无监督学习与模型评估。",
        "provider": "MOOC",
        "url": "https://example.com/ml",
        "category": "人工智能",
        "difficulty": "advanced",
        "duration": 40.0,
        "rating": 4.8,
    },
    {
        "title": "数据科学导论",
        "description": "数据分析流程、可视化与统计基础。",
        "provider": "MOOC",
        "url": "https://example.com/data-science",
        "category": "数据科学",
        "difficulty": "beginner",
        "duration": 24.0,
        "rating": 4.5,
    },
    {
        "title": "Web 应用开发",
        "description": "使用 Flask 构建 Web 应用与 REST 接口。",
        "provider": "MOOC",
        "url": "https://example.com/web",
        "category": "编程",
        "difficulty": "intermediate",
        "duration": 28.0,
        "rating": 4.4,
    },
]

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo1234"

# (课程标题, 先修课程标题)
SAMPLE_PREREQUISITES = [
    ("数据结构与算法", "Python 编程入门"),
    ("机器学习基础", "数据结构与算法"),
    ("机器学习基础", "数据科学导论"),
    ("Web 应用开发", "Python 编程入门"),
]


def register_commands(app):
    @app.cli.command("seed-db")
    def seed_db():
        """写入示例课程、演示用户与推荐数据(可重复执行)。"""
        created_courses = 0
        for data in SAMPLE_COURSES:
            if not Course.query.filter_by(title=data["title"]).first():
                Course.add_course(**data)
                created_courses += 1

        if not User.get_user_by_username(DEMO_USERNAME):
            User.add_user(
                DEMO_USERNAME, "demo@example.com", DEMO_PASSWORD, role="student"
            )

        user = User.get_user_by_username(DEMO_USERNAME)
        created_recs = 0
        for title, score in [("Python 编程入门", 5.0), ("数据结构与算法", 4.0)]:
            course = Course.query.filter_by(title=title).first()
            if course and not Recommendation.query.filter_by(
                user_id=user.id, course_id=course.id
            ).first():
                Recommendation.add_recommendation(user.id, course.id, score)
                created_recs += 1

        created_links = 0
        for course_title, prerequisite_title in SAMPLE_PREREQUISITES:
            course = Course.query.filter_by(title=course_title).first()
            prerequisite = Course.query.filter_by(title=prerequisite_title).first()
            if course and prerequisite and prerequisite not in course.prerequisites:
                course.add_prerequisite(prerequisite)
                created_links += 1

        click.echo(
            f"seeded {created_courses} courses, {created_recs} recommendations, "
            f"{created_links} prerequisite links "
            f"(demo user: {DEMO_USERNAME}/{DEMO_PASSWORD})"
        )

        try:
            from app.models.knowledge_graph import KnowledgeGraph
            from app.utils.neo4j_utils import get_neo4j_db

            kg = KnowledgeGraph(get_neo4j_db())
            for course in Course.query.all():
                if not kg.find_concept(f"Course_{course.id}"):
                    kg.create_concept(f"Course_{course.id}", course.title)
            click.echo("knowledge graph seeded")
        except Exception as exc:  # Neo4j 不可用时跳过
            click.echo(f"skipped knowledge graph seed: {exc}")

    @app.cli.command("experiment-report")
    def experiment_report():
        """打印 A/B 实验报告(按分组统计满意度与 CTR)。"""
        from app.services.experiment_service import (
            ExperimentService,
            DEFAULT_EXPERIMENT,
        )

        report = ExperimentService().report(DEFAULT_EXPERIMENT)
        click.echo(f"experiment: {DEFAULT_EXPERIMENT}")
        for variant, metrics in report.items():
            click.echo(f"  {variant}: {metrics}")

    @app.cli.command("import-courses")
    @click.option(
        "--source",
        "sources",
        multiple=True,
        help="数据源 URL 或本地 JSON 文件路径(可多次指定;默认使用配置/内置样例)。",
    )
    def import_courses(sources):
        """从数据源导入课程(按标题去重)。"""
        from app.services.course_import_service import CourseImportService

        created, skipped = CourseImportService().import_courses(list(sources) or None)
        click.echo(f"imported {created} courses, skipped {skipped} duplicates")
