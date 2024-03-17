from app import db


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    provider = db.Column(db.String(50))
    url = db.Column(db.String(200))
    category = db.Column(db.String(50))
    difficulty = db.Column(db.String(20))
    duration = db.Column(db.Float)
    rating = db.Column(db.Float)

    def __repr__(self):
        return f"<Course {self.title}>"

    @staticmethod
    def add_course(
        title, description, provider, url, category, difficulty, duration, rating
    ):
        course = Course(
            title=title,
            description=description,
            provider=provider,
            url=url,
            category=category,
            difficulty=difficulty,
            duration=duration,
            rating=rating,
        )
        db.session.add(course)
        db.session.commit()
        return course

    @staticmethod
    def get_course_by_id(course_id):
        return Course.query.get(course_id)

    @staticmethod
    def get_courses_by_category(category):
        return Course.query.filter_by(category=category).all()

    @staticmethod
    def get_courses_by_difficulty(difficulty):
        return Course.query.filter_by(difficulty=difficulty).all()

    @staticmethod
    def get_top_rated_courses(limit=10):
        return Course.query.order_by(Course.rating.desc()).limit(limit).all()

    @staticmethod
    def search_courses(keyword):
        return Course.query.filter(Course.title.like(f"%{keyword}%")).all()
