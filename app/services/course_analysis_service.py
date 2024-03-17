import requests
from app.models.knowledge_graph import KnowledgeGraph
from app.utils.neo4j_utils import get_neo4j_graph


class CourseAnalysisService:
    def __init__(self):
        self.neo4j_graph = get_neo4j_graph("bolt://localhost:7687", "neo4j", "password")
        self.knowledge_graph = KnowledgeGraph(self.neo4j_graph)

    def fetch_course_data(self):
        course_data_urls = [
            "https://api.example.com/courses",
            "https://api.example.com/coursedetails",
        ]
        course_data = []

        for url in course_data_urls:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                course_data.extend(data["courses"])

        return course_data

    def analyze_course_topics(self, course_data):
        course_topics = {}

        for course in course_data:
            course_id = course["id"]
            title = course["title"]
            description = course["description"]

            topics = self._perform_topic_modeling(title, description)
            course_topics[course_id] = topics

        return course_topics

    def _perform_topic_modeling(self, title, description):
        # Placeholder implementation
        # Replace with actual topic modeling algorithm
        topics = ["Topic 1", "Topic 2", "Topic 3"]
        return topics

    def build_course_knowledge_graph(self, course_topics):
        for course_id, topics in course_topics.items():
            course_node = self.knowledge_graph.create_concept(
                f"Course_{course_id}", f"Course {course_id}"
            )

            for topic in topics:
                topic_node = self.knowledge_graph.find_concept(topic)
                if not topic_node:
                    topic_node = self.knowledge_graph.create_concept(
                        topic, f"Topic: {topic}"
                    )

                self.knowledge_graph.create_relationship(
                    course_node, topic_node, "HAS_TOPIC"
                )

        return self.knowledge_graph
