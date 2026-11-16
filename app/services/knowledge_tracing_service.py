"""轻量知识追踪(Knowledge Tracing)。

参考:
- Corbett & Anderson, *Knowledge Tracing: Modeling the Acquisition of
  Procedural Knowledge* (1995) 的 Bayesian Knowledge Tracing(BKT)。
- Nakagawa et al., *Graph-based Knowledge Tracing* (2019) 的图结构思想;
  本模块只做 BKT 更新,图传播由 ``concept_graph_service`` 负责。

不依赖 PyTorch/TensorFlow,只使用 Python 标准库,保证 CI 与离线环境可用。
"""

import math
from datetime import datetime

from app import db
from app.models.interaction import (
    EVENT_ANSWER,
    EVENT_COMPLETE,
    EVENT_TYPES,
    Interaction,
    KnowledgeState,
)
from app.services.experiment_service import DEFAULT_EXPERIMENT


DEFAULT_PARAMS = {
    "p_init": 0.30,   # 初始掌握概率
    "p_learn": 0.15,  # 每次练习后的学习概率
    "p_slip": 0.10,   # 已掌握却答错的概率
    "p_guess": 0.20,  # 未掌握却答对的概率
}

# 遗忘曲线:30 天不练习,掌握度衰减一半。
DEFAULT_HALF_LIFE_DAYS = 30.0
MIN_MASTERY = 0.01
MAX_MASTERY = 0.99


def course_concept(course_id):
    """没有细粒度概念数据时的稳定回退键。"""
    return f"Course_{course_id}"


class KnowledgeTracingService:
    def __init__(self, params=None):
        self.params = dict(DEFAULT_PARAMS)
        if params:
            self.params.update(params)

    # ------------------------------------------------------------------
    # 概率更新(纯函数,便于单元测试)
    # ------------------------------------------------------------------
    def posterior_correct(self, prior, p_slip=None, p_guess=None):
        p_slip = self.params["p_slip"] if p_slip is None else p_slip
        p_guess = self.params["p_guess"] if p_guess is None else p_guess
        numerator = prior * (1.0 - p_slip)
        denominator = numerator + (1.0 - prior) * p_guess
        return 0.5 if denominator <= 0 else numerator / denominator

    def posterior_incorrect(self, prior, p_slip=None, p_guess=None):
        p_slip = self.params["p_slip"] if p_slip is None else p_slip
        p_guess = self.params["p_guess"] if p_guess is None else p_guess
        numerator = prior * p_slip
        denominator = numerator + (1.0 - prior) * (1.0 - p_guess)
        return 0.5 if denominator <= 0 else numerator / denominator

    def update_mastery(self, prior, correct):
        """一次 BKT 更新:先贝叶斯后验,再叠加学习转移。"""
        if correct:
            posterior = self.posterior_correct(prior)
        else:
            posterior = self.posterior_incorrect(prior)
        learned = posterior + (1.0 - posterior) * self.params["p_learn"]
        return self._clamp(learned)

    @staticmethod
    def _clamp(value):
        return max(MIN_MASTERY, min(MAX_MASTERY, float(value)))

    @staticmethod
    def _decay(mastery, updated_at):
        if not updated_at:
            return mastery
        days = max(
            (datetime.utcnow() - updated_at).total_seconds() / 86400.0, 0.0
        )
        return mastery * math.pow(0.5, days / DEFAULT_HALF_LIFE_DAYS)

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def get_state(self, user_id, concept):
        return KnowledgeState.query.filter_by(
            user_id=user_id, concept=concept
        ).first()

    def mastery_for(self, user_id, concept):
        state = self.get_state(user_id, concept)
        if not state:
            return self.params["p_init"]
        return self._clamp(self._decay(state.mastery, state.updated_at))

    def record_interaction(
        self,
        user_id,
        course_id,
        concept=None,
        correct=True,
        response_time=None,
        event_type=EVENT_ANSWER,
        experiment=DEFAULT_EXPERIMENT,
        variant=None,
        commit=True,
    ):
        """写入交互事件并更新知识点掌握度,返回 ``(interaction, state)``。

        ``complete`` 事件只记录完成状态,不参与 BKT 更新;若此前没有掌握度
        记录,返回的 ``state`` 为 ``None``。
        """
        event_type = (event_type or EVENT_ANSWER).strip().lower()
        if event_type not in EVENT_TYPES:
            event_type = EVENT_ANSWER

        concept = (concept or "").strip() or course_concept(course_id)
        interaction = Interaction(
            user_id=user_id,
            course_id=course_id,
            experiment=experiment or DEFAULT_EXPERIMENT,
            variant=variant,
            concept=concept,
            event_type=event_type,
            correct=bool(correct) if event_type == EVENT_ANSWER else False,
            response_time=response_time,
        )
        db.session.add(interaction)

        state = self.get_state(user_id, concept)
        if event_type == EVENT_COMPLETE:
            # 完成课程不等于答对,不更新掌握度;只复用已有状态用于响应。
            if commit:
                db.session.commit()
            else:
                db.session.flush()
            return interaction, state

        prior = (
            self._decay(state.mastery, state.updated_at)
            if state
            else self.params["p_init"]
        )
        mastery = self.update_mastery(prior, bool(correct))
        if state:
            state.mastery = mastery
            state.updated_at = datetime.utcnow()
        else:
            state = KnowledgeState(
                user_id=user_id,
                concept=concept,
                mastery=mastery,
                updated_at=datetime.utcnow(),
            )
            db.session.add(state)

        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return interaction, state

    def mastery_map(self, user_id, decay=True):
        """返回 ``{concept: mastery}``;默认按遗忘曲线做时间衰减。"""
        states = KnowledgeState.query.filter_by(user_id=user_id).all()
        result = {}
        for state in states:
            mastery = state.mastery
            if decay:
                mastery = self._decay(mastery, state.updated_at)
            result[state.concept] = self._clamp(mastery)
        return result

    def predict_correct(self, user_id, concept):
        """预测下一次作答正确的概率(使用衰减后的掌握度)。"""
        mastery = self.mastery_map(user_id).get(concept, self.params["p_init"])
        return (
            mastery * (1.0 - self.params["p_slip"])
            + (1.0 - mastery) * self.params["p_guess"]
        )
