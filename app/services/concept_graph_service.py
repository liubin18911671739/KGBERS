"""概念图上的轻量掌握度传播。

参考 TransKT(Han et al., IJCAI 2025)的 "concept graph guided knowledge
transfer" 思想,把 GCN 替换为可解释的迭代标签传播:

    S^(t+1) = (1 - alpha) * S^(t) + alpha * A_norm * S^(t)

图中的节点包括:
- ``Course_<id>``:课程节点;
- ``Category_<category>``:类别节点(同类课程之间迁移);
- ``Topic_<topic>``:Neo4j 中的主题节点(跨课程概念迁移)。

另外用课程标题关键词共现生成跨类别课程的弱链接(过滤过高频词),近似
TransKT 的隐式跨课程概念链接。Neo4j 不可用时自动退化为「课程节点 + 类别
节点 + 先修边 + 标题共现」,并短时熔断,不阻塞推荐。
"""

import re
import time
from collections import defaultdict

from sqlalchemy.orm import selectinload

from app.models.course import Course
from app.services.completion_service import (
    completed_course_ids as get_completed_course_ids,
)
from app.services.knowledge_tracing_service import (
    KnowledgeTracingService,
    course_concept,
)
from app.utils.neo4j_utils import get_neo4j_db


CATEGORY_WEIGHT = 0.75
TOPIC_WEIGHT = 0.90
PREREQUISITE_WEIGHT = 1.00
TITLE_TOKEN_WEIGHT = 0.55
TITLE_TOKEN_MAX_DF_RATIO = 0.10
DEFAULT_ALPHA = 0.25
DEFAULT_ITERATIONS = 6
DEFAULT_UNKNOWN_MASTERY = 0.5
PREREQUISITE_MASTERY_THRESHOLD = 0.60
TITLE_STOPWORDS = {"基础", "入门", "导论", "高级", "与", "的", "和"}
NEO4J_RETRY_SECONDS = 60.0

# Neo4j 不可用时短时熔断,避免学习路径/自适应推荐每次请求都等待连接失败。
_NEO4J_BACKOFF_UNTIL = 0.0


def reset_neo4j_backoff():
    """测试/运维使用:清除 Neo4j 熔断状态。"""
    global _NEO4J_BACKOFF_UNTIL
    _NEO4J_BACKOFF_UNTIL = 0.0


class ConceptGraphService:
    def __init__(self, tracing_service=None):
        self.tracing = tracing_service or KnowledgeTracingService()
        self._graph = None
        self._course_concepts = {}

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------
    def graph(self, courses=None):
        if self._graph is not None and courses is None:
            return self._graph
        self._build_graph(courses)
        return self._graph

    def _build_graph(self, courses=None):
        if courses is None:
            courses = Course.query.options(
                selectinload(Course.prerequisites)
            ).all()
        else:
            courses = list(courses)
        adjacency = defaultdict(dict)
        course_concepts = {}
        topics_by_course = self._topics_for_courses([course.id for course in courses])

        for course in courses:
            node = course_concept(course.id)
            concepts = [node]

            if course.category:
                category_node = f"Category_{course.category}"
                concepts.append(category_node)
                self._add_edge(adjacency, node, category_node, CATEGORY_WEIGHT)

            for topic in sorted(topics_by_course.get(course.id, ())):
                topic_node = f"Topic_{topic}"
                concepts.append(topic_node)
                self._add_edge(adjacency, node, topic_node, TOPIC_WEIGHT)

            for prerequisite in course.prerequisites:
                prerequisite_node = course_concept(prerequisite.id)
                self._add_edge(
                    adjacency, prerequisite_node, node, PREREQUISITE_WEIGHT
                )

            course_concepts[course.id] = concepts

        # 标题关键词共现:跨类别课程的轻量“概念链接”,对应 TransKT 的
        # implicit cross-course concept links(不依赖 LLM)。
        token_index = defaultdict(set)
        for course in courses:
            for token in self._title_tokens(course.title):
                token_index[token].add(course.id)
        max_df = max(2, int(len(courses) * TITLE_TOKEN_MAX_DF_RATIO))
        for course_ids in token_index.values():
            if len(course_ids) > max_df:
                # 过滤“数据/课程”等过于通用的词,避免全图过度连接。
                continue
            ordered = sorted(course_ids)
            for index, source_id in enumerate(ordered):
                for target_id in ordered[index + 1:]:
                    self._add_edge(
                        adjacency,
                        course_concept(source_id),
                        course_concept(target_id),
                        TITLE_TOKEN_WEIGHT,
                    )

        for course in courses:
            adjacency.setdefault(course_concept(course.id), {})

        self._graph = dict(adjacency)
        self._course_concepts = course_concepts

    @staticmethod
    def _add_edge(adjacency, source, target, weight):
        if source == target:
            return
        adjacency[source][target] = max(
            adjacency[source].get(target, 0.0), float(weight)
        )
        adjacency[target][source] = max(
            adjacency[target].get(source, 0.0), float(weight)
        )

    @staticmethod
    def _title_tokens(title):
        tokens = set()
        for chunk in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", (title or "").lower()):
            if chunk.isascii():
                if len(chunk) >= 2:
                    tokens.add(chunk)
                continue
            if len(chunk) == 1:
                tokens.add(chunk)
            else:
                tokens.update(chunk[i : i + 2] for i in range(len(chunk) - 1))
        return {token for token in tokens if token not in TITLE_STOPWORDS}

    def _topics_for_courses(self, course_ids):
        """一次 Cypher 查询取回多门课程的主题;Neo4j 不可用时返回空。"""
        global _NEO4J_BACKOFF_UNTIL

        if not course_ids:
            return {}
        if time.monotonic() < _NEO4J_BACKOFF_UNTIL:
            return {}
        try:
            graph = get_neo4j_db()
            names = [course_concept(course_id) for course_id in course_ids]
            rows = graph.run(
                "MATCH (c:Concept)-[:HAS_TOPIC]->(t:Concept) "
                "WHERE c.name IN $names "
                "RETURN c.name AS course, t.name AS topic",
                names=names,
            ).data()
        except Exception:
            # 与 recommendation_service 一致:Neo4j 是可选增强。
            # 失败后短时熔断,避免每次请求都等待连接超时。
            _NEO4J_BACKOFF_UNTIL = time.monotonic() + NEO4J_RETRY_SECONDS
            return {}

        topics_map = {}
        for row in rows:
            course_name = row.get("course") or ""
            topic = row.get("topic")
            if not topic or not course_name.startswith("Course_"):
                continue
            try:
                course_id = int(course_name.rsplit("_", 1)[1])
            except (IndexError, ValueError):
                continue
            topics_map.setdefault(course_id, set()).add(topic)
        return topics_map

    # ------------------------------------------------------------------
    # 传播与查询
    # ------------------------------------------------------------------
    def course_concepts(self, course_id):
        self.graph()
        return list(self._course_concepts.get(course_id, [course_concept(course_id)]))

    def propagate_mastery(
        self,
        user_id,
        alpha=DEFAULT_ALPHA,
        iterations=DEFAULT_ITERATIONS,
        courses=None,
    ):
        """在概念图上迭代传播掌握度,返回 ``{concept: mastery}``。"""
        # 复制邻接表,避免把临时种子节点写回图缓存。
        adjacency = {
            node: dict(neighbors)
            for node, neighbors in self.graph(courses).items()
        }
        seeds = self.tracing.mastery_map(user_id)

        nodes = set(adjacency) | set(seeds)
        for node in nodes:
            adjacency.setdefault(node, {})

        values = {}
        for node in nodes:
            if node in seeds:
                values[node] = seeds[node]
                continue
            if node.startswith("Course_"):
                # 未直接观测的课程从 0 开始,由邻居(类别/主题/先修)传播得到。
                values[node] = 0.0
                continue
            neighbor_values = [
                seeds[neighbor]
                for neighbor in adjacency[node]
                if neighbor in seeds
            ]
            # 类别/主题节点用相邻已观测课程的平均掌握度作为初始值。
            values[node] = (
                sum(neighbor_values) / len(neighbor_values)
                if neighbor_values
                else 0.0
            )

        for _ in range(max(0, iterations)):
            updated = {}
            for node in nodes:
                neighbors = adjacency[node]
                if neighbors:
                    total = sum(
                        weight * values[neighbor]
                        for neighbor, weight in neighbors.items()
                    )
                    norm = sum(neighbors.values())
                    neighbor_average = total / norm if norm else values[node]
                else:
                    neighbor_average = values[node]
                updated[node] = (
                    (1.0 - alpha) * values[node] + alpha * neighbor_average
                )
            values = updated

        return values

    def course_readiness(
        self,
        user_id,
        course_id,
        mastery=None,
        completed_course_ids=None,
        course=None,
    ):
        """课程级掌握度、先修准备度与学习缺口。"""
        mastery = mastery if mastery is not None else self.propagate_mastery(user_id)
        concepts = self.course_concepts(course_id)
        course_node = course_concept(course_id)

        course_value = mastery.get(course_node, DEFAULT_UNKNOWN_MASTERY)
        other_values = [
            mastery.get(concept, DEFAULT_UNKNOWN_MASTERY)
            for concept in concepts
            if concept != course_node
        ]
        if other_values:
            course_mastery = 0.6 * course_value + 0.4 * (
                sum(other_values) / len(other_values)
            )
        else:
            course_mastery = course_value

        course = course or Course.get_course_by_id(course_id)
        prerequisites = list(course.prerequisites) if course else []
        if completed_course_ids is None:
            completed_course_ids = get_completed_course_ids(user_id)
        completed_course_ids = set(completed_course_ids)

        if prerequisites:
            ready = 0
            for prerequisite in prerequisites:
                prerequisite_mastery = mastery.get(
                    course_concept(prerequisite.id), DEFAULT_UNKNOWN_MASTERY
                )
                if (
                    prerequisite.id in completed_course_ids
                    or prerequisite_mastery >= PREREQUISITE_MASTERY_THRESHOLD
                ):
                    ready += 1
            prerequisite_readiness = ready / len(prerequisites)
        else:
            prerequisite_readiness = 1.0

        return {
            "course_id": course_id,
            "concepts": concepts,
            "mastery": max(0.0, min(1.0, course_mastery)),
            "mastery_gap": max(0.0, min(1.0, 1.0 - course_mastery)),
            "prerequisite_readiness": prerequisite_readiness,
        }
