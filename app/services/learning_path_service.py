from collections import deque

from app.models.course import Course
from app.models.recommendation import Recommendation
from app.services.recommendation_service import DIFFICULTY_ORDER


class LearningPathService:
    def build_path(self, target_course_id):
        """
        基于先修关系生成从基础到目标课程的学习序列。

        - 收集目标课程的全部(传递)先修课程;
        - 对子图做 Kahn 拓扑排序(先修在前);
        - 同层按难度升序、评分降序、id 升序稳定排序;
        - 检测到环时,环上课程按难度/评分兜底排列。
        """
        target = Course.get_course_by_id(target_course_id)
        if not target:
            return []

        courses = {target.id: target}
        for prerequisite_id in self._collect_ancestor_ids(target):
            course = Course.get_course_by_id(prerequisite_id)
            if course:
                courses[course.id] = course

        node_ids = set(courses)
        edges = {course_id: set() for course_id in node_ids}
        indegree = {course_id: 0 for course_id in node_ids}

        for course_id, course in courses.items():
            for prerequisite in course.prerequisites:
                if prerequisite.id in node_ids:
                    edges[prerequisite.id].add(course_id)
                    indegree[course_id] += 1

        ready = sorted(
            (cid for cid in node_ids if indegree[cid] == 0),
            key=lambda cid: self._sort_key(courses[cid]),
        )
        order = []
        while ready:
            course_id = ready.pop(0)
            order.append(course_id)
            for dependent_id in edges[course_id]:
                indegree[dependent_id] -= 1
                if indegree[dependent_id] == 0:
                    ready.append(dependent_id)
            ready.sort(key=lambda cid: self._sort_key(courses[cid]))

        # 环兜底:未排序的节点按难度/评分补齐
        if len(order) < len(node_ids):
            remaining = node_ids - set(order)
            order.extend(
                sorted(remaining, key=lambda cid: self._sort_key(courses[cid]))
            )

        return [self._serialize(courses[cid]) for cid in order]

    def path_for_user(self, user_id, target_course_id):
        path = self.build_path(target_course_id)
        completed = {
            rec.course_id
            for rec in Recommendation.query.filter_by(user_id=user_id).all()
        }
        for step in path:
            step["completed"] = step["course_id"] in completed
        return path

    @staticmethod
    def _collect_ancestor_ids(target):
        seen = set()
        queue = deque([target])
        while queue:
            course = queue.popleft()
            for prerequisite in course.prerequisites:
                if prerequisite.id not in seen:
                    seen.add(prerequisite.id)
                    queue.append(prerequisite)
        return seen

    @staticmethod
    def _sort_key(course):
        return (
            DIFFICULTY_ORDER.get((course.difficulty or "").lower(), 1),
            -(course.rating or 0.0),
            course.id,
        )

    @staticmethod
    def _serialize(course):
        return {
            "course_id": course.id,
            "title": course.title,
            "category": course.category,
            "difficulty": course.difficulty,
            "completed": False,
        }
