from app.models.recommendation import Recommendation
from app.models.course import Course
from app.models.user import User
from app.utils.neo4j_utils import get_neo4j_db


DIFFICULTY_ORDER = {
    "beginner": 0,
    "easy": 0,
    "intermediate": 1,
    "medium": 1,
    "advanced": 2,
    "hard": 2,
    "expert": 3,
}


class RecommendationService:
    def get_user_recommendations(self, user_id, limit=10):
        recommendations = (
            Recommendation.query.filter_by(user_id=user_id)
            .order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        return recommendations

    def get_course_recommendations(self, course_id, limit=10):
        recommendations = (
            Recommendation.query.filter_by(course_id=course_id)
            .order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        return recommendations

    def get_top_recommendations(self, limit=10):
        recommendations = (
            Recommendation.query.order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        return recommendations

    def add_recommendation(self, user_id, course_id, score):
        user = User.query.get(user_id)
        course = Course.query.get(course_id)

        if user and course:
            recommendation = Recommendation(user=user, course=course, score=score)
            recommendation.save()
            return recommendation
        else:
            return None

    def update_recommendation(self, recommendation_id, score):
        recommendation = Recommendation.query.get(recommendation_id)

        if recommendation:
            recommendation.score = score
            recommendation.save()
            return recommendation
        else:
            return None

    def delete_recommendation(self, recommendation_id):
        recommendation = Recommendation.query.get(recommendation_id)

        if recommendation:
            recommendation.delete()
            return True
        else:
            return False

    def recommend_for_user(self, user_id, limit=10):
        """
        基于内容(类别/难度) + 协同(评分质量) + 知识图谱(共享主题)的混合推荐。

        无历史或无 Neo4j 时仍可工作:内容/协同信号降级,图谱信号置 0。
        """
        user = User.query.get(user_id)
        if not user:
            return []

        user_recs = Recommendation.query.filter_by(user_id=user_id).all()
        rated_course_ids = {rec.course_id for rec in user_recs}

        preferred_categories = {}
        preferred_difficulties = []
        for rec in user_recs:
            if not rec.course:
                continue
            category = rec.course.category
            if category:
                preferred_categories[category] = preferred_categories.get(category, 0) + 1
            if rec.course.difficulty:
                preferred_difficulties.append(rec.course.difficulty)

        quality = self._course_quality()
        user_topics = self._get_course_topics(rated_course_ids)

        courses = Course.query.all()
        # 一次查询取回所有候选课程的图谱主题,避免逐课程访问 Neo4j(N+1)。
        course_topics_map = self._get_topics_for_courses(
            [course.id for course in courses]
        )

        results = []
        for course in courses:
            if course.id in rated_course_ids:
                continue

            content_score = self._content_score(
                course, preferred_categories, preferred_difficulties
            )
            quality_score = min(quality.get(course.id, 0.0) or 0.0, 5.0) / 5.0
            kg_score = self._kg_score(course_topics_map.get(course.id, set()), user_topics)

            score = 0.5 * content_score + 0.3 * quality_score + 0.2 * kg_score
            results.append(
                {
                    "course_id": course.id,
                    "title": course.title,
                    "category": course.category,
                    "difficulty": course.difficulty,
                    "score": round(score, 4),
                }
            )

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]

    @staticmethod
    def _course_quality():
        quality = {}
        for rec in Recommendation.query.all():
            total, count = quality.get(rec.course_id, (0.0, 0))
            quality[rec.course_id] = (total + (rec.score or 0.0), count + 1)
        return {course_id: total / count for course_id, (total, count) in quality.items()}

    @staticmethod
    def _difficulty_rank(difficulties):
        ranks = [DIFFICULTY_ORDER.get((d or "").lower(), 1) for d in difficulties]
        return sum(ranks) / len(ranks) if ranks else 1.0

    def _content_score(self, course, preferred_categories, preferred_difficulties):
        if not preferred_categories and not preferred_difficulties:
            return 0.5

        score = 0.0
        if preferred_categories and course.category:
            top = max(preferred_categories.values())
            score += 0.5 * (preferred_categories.get(course.category, 0) / top)

        if preferred_difficulties and course.difficulty:
            target = self._difficulty_rank(preferred_difficulties)
            rank = self._difficulty_rank([course.difficulty])
            score += 0.5 * (1.0 - min(abs(target - rank), 3) / 3.0)

        return score

    @staticmethod
    def _get_course_topics(course_ids):
        topics_map = RecommendationService._get_topics_for_courses(course_ids)
        combined = set()
        for topics in topics_map.values():
            combined.update(topics)
        return combined

    @staticmethod
    def _get_topics_for_courses(course_ids):
        """一次 Cypher 查询取回多门课程的主题,返回 {course_id: {topic}}。"""
        if not course_ids:
            return {}
        try:
            graph = get_neo4j_db()
            names = [f"Course_{course_id}" for course_id in course_ids]
            rows = graph.run(
                "MATCH (c:Concept)-[:HAS_TOPIC]->(t:Concept) "
                "WHERE c.name IN $names "
                "RETURN c.name AS course, t.name AS topic",
                names=names,
            ).data()
        except Exception:
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

    @staticmethod
    def _kg_score(course_topics, user_topics):
        if not user_topics or not course_topics:
            return 0.0
        return len(course_topics & user_topics) / len(course_topics | user_topics)
