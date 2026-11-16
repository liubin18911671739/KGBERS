from datetime import datetime, timedelta

import pytest

from app.models.course import Course
from app.models.interaction import Interaction, KnowledgeState
from app.models.user import User
from app.services.knowledge_tracing_service import (
    KnowledgeTracingService,
    course_concept,
)


def _course(title="C", category="编程"):
    return Course.add_course(title, "d", "p", "u", category, "beginner", 1, 4.0)


def test_bkt_correct_increases_mastery():
    service = KnowledgeTracingService()

    learned = service.update_mastery(0.30, correct=True)
    forgotten = service.update_mastery(0.30, correct=False)

    assert learned > 0.30
    assert forgotten < 0.30
    assert 0.0 < learned < 1.0
    assert 0.0 < forgotten < 1.0


def test_record_interaction_persists_and_updates_state(app):
    user = User.add_user("u", "u@example.com", "pw")
    course = _course()
    service = KnowledgeTracingService()

    interaction, state = service.record_interaction(
        user.id, course.id, correct=True
    )

    assert Interaction.query.count() == 1
    assert interaction.concept == course_concept(course.id)
    assert KnowledgeState.query.count() == 1
    assert state.mastery > service.params["p_init"]
    assert service.mastery_for(
        user.id, course_concept(course.id)
    ) == pytest.approx(state.mastery, rel=0.01)


def test_repeated_interactions_share_one_state(app):
    user = User.add_user("u", "u@example.com", "pw")
    course = _course()
    service = KnowledgeTracingService()

    service.record_interaction(user.id, course.id, correct=True)
    service.record_interaction(user.id, course.id, correct=True)

    assert Interaction.query.count() == 2
    assert KnowledgeState.query.count() == 1
    assert KnowledgeState.query.one().mastery > service.params["p_init"]


def test_mastery_map_applies_forgetting_curve(app):
    user = User.add_user("u", "u@example.com", "pw")
    course = _course()
    old = datetime.utcnow() - timedelta(days=60)
    KnowledgeState(
        user_id=user.id,
        concept=course_concept(course.id),
        mastery=0.80,
        updated_at=old,
    ).save()

    mastery = KnowledgeTracingService().mastery_map(user.id)

    # 30 天半衰期,60 天后约剩 0.2。
    assert mastery[course_concept(course.id)] < 0.30


def test_predict_correct_is_probability(app):
    user = User.add_user("u", "u@example.com", "pw")
    course = _course()

    probability = KnowledgeTracingService().predict_correct(
        user.id, course_concept(course.id)
    )

    assert 0.0 <= probability <= 1.0
