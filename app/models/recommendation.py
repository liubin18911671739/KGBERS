from app import db


class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    score = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("recommendations", lazy=True))
    course = db.relationship("Course", backref=db.backref("recommendations", lazy=True))

    def __repr__(self):
        return f"<Recommendation {self.user.username} - {self.course.title}>"

    @staticmethod
    def add_recommendation(user_id, course_id, score):
        recommendation = Recommendation(
            user_id=user_id, course_id=course_id, score=score
        )
        db.session.add(recommendation)
        db.session.commit()
        return recommendation

    @staticmethod
    def get_user_recommendations(user_id, limit=10):
        recommendations = (
            Recommendation.query.filter_by(user_id=user_id)
            .order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        return recommendations

    @staticmethod
    def get_course_recommendations(course_id, limit=10):
        recommendations = (
            Recommendation.query.filter_by(course_id=course_id)
            .order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        return recommendations

    @staticmethod
    def get_top_recommendations(limit=10):
        recommendations = (
            Recommendation.query.order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        return recommendations
