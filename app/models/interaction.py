from datetime import datetime

from app import db


EVENT_ANSWER = "answer"
EVENT_COMPLETE = "complete"
EVENT_TYPES = (EVENT_ANSWER, EVENT_COMPLETE)


class Interaction(db.Model):
    """学习者与课程/知识点的一次交互(答题、完成课程等)。

    这是轻量知识追踪(Knowledge Tracing)的输入事件流。`concept` 既可以是
    Neo4j 中的概念名,也可以退化为 `Course_<id>`,保证离线环境可用。

    `event_type` 区分「答题」与「完成课程」:
    - ``answer``:参与 BKT 掌握度更新;
    - ``complete``:只记录完成状态,不把完成当成答对而抬高掌握度。
    """

    __tablename__ = "interaction"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    course_id = db.Column(
        db.Integer, db.ForeignKey("course.id"), nullable=False, index=True
    )
    experiment = db.Column(
        db.String(64),
        nullable=False,
        default="recommendation",
        server_default="recommendation",
        index=True,
    )
    variant = db.Column(db.String(32))
    concept = db.Column(db.String(120), nullable=False, index=True)
    event_type = db.Column(
        db.String(16),
        nullable=False,
        default=EVENT_ANSWER,
        server_default=EVENT_ANSWER,
        index=True,
    )
    correct = db.Column(db.Boolean, nullable=False, default=False)
    response_time = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship(
        "User", backref=db.backref("interactions", lazy=True)
    )
    course = db.relationship(
        "Course", backref=db.backref("interactions", lazy=True)
    )

    def __repr__(self):
        return (
            f"<Interaction user={self.user_id} course={self.course_id} "
            f"concept={self.concept} event={self.event_type} "
            f"experiment={self.experiment}/{self.variant} "
            f"correct={self.correct}>"
        )

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class KnowledgeState(db.Model):
    """用户对某个知识点的当前掌握概率(0~1)。"""

    __tablename__ = "knowledge_state"
    __table_args__ = (
        db.UniqueConstraint("user_id", "concept", name="uq_user_concept"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    concept = db.Column(db.String(120), nullable=False, index=True)
    mastery = db.Column(db.Float, nullable=False, default=0.0)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = db.relationship(
        "User", backref=db.backref("knowledge_states", lazy=True)
    )

    def __repr__(self):
        return (
            f"<KnowledgeState user={self.user_id} concept={self.concept} "
            f"mastery={self.mastery:.4f}>"
        )

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self
