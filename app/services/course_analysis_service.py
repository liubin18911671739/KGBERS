import json
import os

import requests
from app.models.knowledge_graph import KnowledgeGraph
from app.services.course_import_service import CourseImportService
from app.services.topic_modeling_service import TopicModelService
from app.utils.neo4j_utils import get_neo4j_db


SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "samples",
    "mooc_courses.json",
)


class CourseAnalysisService:
    def __init__(self):
        # 惰性初始化:仅在真正需要知识图谱时才连接 Neo4j。
        self.neo4j_graph = None
        self.knowledge_graph = None
        self.topic_model = TopicModelService()
        self.import_service = CourseImportService()

    def _get_knowledge_graph(self):
        if self.knowledge_graph is None:
            self.neo4j_graph = get_neo4j_db()
            self.knowledge_graph = KnowledgeGraph(self.neo4j_graph)
        return self.knowledge_graph

    def fetch_course_data(self, sources=None):
        """
        从配置的数据源(URL 或本地文件)读取课程数据。
        默认使用 config.COURSE_DATA_URLS;未配置时回退到内置样例。
        """
        if sources:
            return self.import_service.fetch_course_data(sources)

        urls = self.import_service.default_sources()
        if urls:
            try:
                return self.import_service.fetch_course_data(urls)
            except (requests.RequestException, ValueError):
                pass

        return self.import_service.fetch_course_data([SAMPLE_PATH])

    def analyze_course_topics(self, course_data):
        documents = [
            f"{course.get('title', '')} {course.get('description', '')}"
            for course in course_data
        ]
        self.topic_model.fit(documents)

        course_topics = {}
        for course in course_data:
            course_id = course.get("id")
            title = course.get("title", "")
            description = course.get("description", "")

            topics = self._perform_topic_modeling(title, description)
            course_topics[course_id] = topics

        return course_topics

    def _perform_topic_modeling(self, title, description, top_n=3):
        """
        主题抽取:优先 gensim LDA(需先 fit 语料),否则降级为词频关键词。
        """
        return self.topic_model.extract(f"{title or ''} {description or ''}", top_n)

    def build_course_knowledge_graph(self, course_topics):
        knowledge_graph = self._get_knowledge_graph()
        for course_id, topics in course_topics.items():
            course_node = knowledge_graph.create_concept(
                f"Course_{course_id}", f"Course {course_id}"
            )

            for topic in topics:
                topic_node = knowledge_graph.find_concept(topic)
                if not topic_node:
                    topic_node = knowledge_graph.create_concept(
                        topic, f"Topic: {topic}"
                    )

                knowledge_graph.create_relationship(
                    course_node, topic_node, "HAS_TOPIC"
                )

        return knowledge_graph
