from datetime import datetime

from app import db


class ExperimentAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    experiment = db.Column(db.String(64), nullable=False)
    variant = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "experiment", name="uq_user_experiment"),
    )

    def __repr__(self):
        return f"<ExperimentAssignment {self.user_id} {self.experiment}={self.variant}>"

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    variant = db.Column(db.String(32))
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Feedback user={self.user_id} course={self.course_id} rating={self.rating}>"

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self


class RecommendationEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    variant = db.Column(db.String(32))
    event_type = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RecommendationEvent {self.event_type} user={self.user_id}>"

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self
