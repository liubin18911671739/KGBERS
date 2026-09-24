import hashlib

from app import db
from app.models.experiment import (
    ExperimentAssignment,
    Feedback,
    RecommendationEvent,
)


DEFAULT_EXPERIMENT = "recommendation"
CONTROL = "control"
TREATMENT = "treatment"
VARIANTS = (CONTROL, TREATMENT)


class ExperimentService:
    def assign(self, user_id, experiment=DEFAULT_EXPERIMENT):
        """返回用户在该实验中的分组;首次访问时确定性分配并落库。"""
        assignment = ExperimentAssignment.query.filter_by(
            user_id=user_id, experiment=experiment
        ).first()
        if assignment:
            return assignment.variant

        variant = self._variant_for(user_id, experiment)
        ExperimentAssignment(
            user_id=user_id, experiment=experiment, variant=variant
        ).save()
        return variant

    @staticmethod
    def _variant_for(user_id, experiment):
        digest = hashlib.md5(f"{experiment}:{user_id}".encode("utf-8")).hexdigest()
        return TREATMENT if int(digest, 16) % 2 == 0 else CONTROL

    def record_feedback(self, user_id, course_id, rating, comment=None, variant=None):
        return Feedback(
            user_id=user_id,
            course_id=course_id,
            rating=int(rating),
            comment=comment,
            variant=variant,
        ).save()

    def record_event(self, user_id, course_id, variant, event_type):
        return RecommendationEvent(
            user_id=user_id,
            course_id=course_id,
            variant=variant,
            event_type=event_type,
        ).save()

    def record_impressions(self, user_id, course_ids, variant):
        """记录曝光;同一用户/课程/分组只记录一次,避免刷新页面重复计数。"""
        existing = {
            course_id
            for (course_id,) in db.session.query(RecommendationEvent.course_id)
            .filter_by(user_id=user_id, variant=variant, event_type="impression")
            .distinct()
            .all()
        }
        for course_id in course_ids:
            if course_id not in existing:
                self.record_event(user_id, course_id, variant, "impression")
                existing.add(course_id)

    def report(self, experiment=DEFAULT_EXPERIMENT):
        assignments = ExperimentAssignment.query.filter_by(experiment=experiment).all()

        report = {}
        for variant in VARIANTS:
            variant_users = {a.user_id for a in assignments if a.variant == variant}
            feedback = Feedback.query.filter_by(variant=variant).all()
            ratings = [item.rating for item in feedback]
            impressions = RecommendationEvent.query.filter_by(
                variant=variant, event_type="impression"
            ).count()
            clicks = RecommendationEvent.query.filter_by(
                variant=variant, event_type="click"
            ).count()

            report[variant] = {
                "users": len(variant_users),
                "feedback_count": len(feedback),
                "avg_rating": round(sum(ratings) / len(ratings), 4) if ratings else None,
                "impressions": impressions,
                "clicks": clicks,
                "ctr": round(clicks / impressions, 4) if impressions else None,
            }

        return report
