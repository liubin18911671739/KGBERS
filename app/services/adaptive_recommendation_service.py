"""自适应推荐(对照实验用)。

把知识追踪(``KnowledgeTracingService``)与概念图传播
(``ConceptGraphService``)的输出作为额外信号,与现有混合推荐分数融合:

    final = 0.6 * baseline + 0.4 * adaptive

``baseline`` 仍是 ``RecommendationService`` 的内容/质量/图谱混合分,因此新算法
只作为 A/B 实验的 treatment 分支,不改变原有推荐行为。
"""

from sqlalchemy.orm import selectinload

from app.models.course import Course
from app.models.user import User
from app.services.completion_service import (
    completed_course_ids as get_completed_course_ids,
)
from app.services.concept_graph_service import ConceptGraphService
from app.services.knowledge_tracing_service import KnowledgeTracingService
from app.services.recommendation_service import (
    DIFFICULTY_ORDER,
    RecommendationService,
)


ADAPTIVE_EXPERIMENT = "adaptive_kt"
ADAPTIVE_WEIGHT = 0.4


class AdaptiveRecommendationService:
    def __init__(
        self,
        baseline_service=None,
        tracing_service=None,
        graph_service=None,
    ):
        self.baseline_service = baseline_service or RecommendationService()
        self.tracing_service = tracing_service or KnowledgeTracingService()
        self.graph_service = graph_service or ConceptGraphService(
            tracing_service=self.tracing_service
        )

    def recommend_for_user(self, user_id, limit=10):
        user = User.query.get(user_id)
        if not user:
            return []

        courses = self._load_courses()
        # 让 baseline 返回全部候选,避免 1000 条截断后无法重新排序。
        baseline = self.baseline_service.recommend_for_user(user_id, limit=None)
        if not baseline:
            return []

        completed = get_completed_course_ids(user_id)
        mastery = self.graph_service.propagate_mastery(
            user_id, courses=courses.values()
        )
        difficulty_target = self._difficulty_target(completed)

        results = []
        for item in baseline:
            course = courses.get(item["course_id"])
            if not course:
                continue

            enriched, readiness = self._explain(
                user_id, item, course, mastery, completed
            )
            adaptive_score = self._adaptive_score(
                readiness, course.difficulty, difficulty_target
            )
            baseline_score = float(item.get("score") or 0.0)
            final_score = (
                (1.0 - ADAPTIVE_WEIGHT) * baseline_score
                + ADAPTIVE_WEIGHT * adaptive_score
            )
            enriched["score"] = round(final_score, 4)
            enriched["baseline_score"] = round(baseline_score, 4)
            enriched["adaptive_score"] = round(adaptive_score, 4)
            results.append(enriched)

        results.sort(key=lambda item: (-item["score"], item["course_id"]))
        return results[:limit]

    def add_explanations(self, user_id, recommendations):
        """为对照组补齐与 treatment 相同的解释字段,避免 A/B UI 混淆。"""
        if not recommendations:
            return recommendations
        courses = self._load_courses()
        completed = get_completed_course_ids(user_id)
        mastery = self.graph_service.propagate_mastery(
            user_id, courses=courses.values()
        )

        explained = []
        for item in recommendations:
            course = courses.get(item["course_id"])
            if not course:
                explained.append(item)
                continue
            enriched, _ = self._explain(
                user_id, item, course, mastery, completed
            )
            explained.append(enriched)
        return explained

    def _explain(self, user_id, item, course, mastery, completed):
        readiness = self.graph_service.course_readiness(
            user_id,
            course.id,
            mastery=mastery,
            completed_course_ids=completed,
            course=course,
        )
        enriched = dict(item)
        enriched["mastery"] = round(readiness["mastery"], 4)
        enriched["prerequisite_readiness"] = round(
            readiness["prerequisite_readiness"], 4
        )
        enriched["reason"] = self._reason(readiness)
        return enriched, readiness

    @staticmethod
    def _load_courses():
        return {
            course.id: course
            for course in Course.query.options(
                selectinload(Course.prerequisites)
            ).all()
        }

    def _adaptive_score(self, readiness, difficulty, difficulty_target):
        mastery_gap = readiness["mastery_gap"]
        prerequisite_readiness = readiness["prerequisite_readiness"]

        rank = DIFFICULTY_ORDER.get((difficulty or "").lower(), 1)
        difficulty_fit = 1.0 - min(abs(rank - difficulty_target) / 3.0, 1.0)

        # 最近发展区:掌握度接近 0.5 时收益最大。
        zpd = 1.0 - min(abs(readiness["mastery"] - 0.5) * 2.0, 1.0)

        score = (
            0.45 * mastery_gap
            + 0.30 * prerequisite_readiness
            + 0.15 * zpd
            + 0.10 * difficulty_fit
        )
        return max(0.0, min(1.0, score))

    @staticmethod
    def _reason(readiness):
        mastery = readiness["mastery"]
        if mastery < 0.35:
            level = "掌握度较低,建议优先补齐"
        elif mastery < 0.70:
            level = "处于最近发展区,适合现在学习"
        else:
            level = "已较熟悉,可作为巩固或进阶"
        return (
            f"{level};当前掌握度 {mastery:.2f},"
            f"先修准备度 {readiness['prerequisite_readiness']:.2f}"
        )

    @staticmethod
    def _completed_course_ids(user_id):
        return get_completed_course_ids(user_id)

    @staticmethod
    def _difficulty_target(completed_course_ids):
        ranks = []
        for course_id in completed_course_ids:
            course = Course.get_course_by_id(course_id)
            if course and course.difficulty:
                ranks.append(
                    DIFFICULTY_ORDER.get((course.difficulty or "").lower(), 1)
                )
        return sum(ranks) / len(ranks) if ranks else 1.0
