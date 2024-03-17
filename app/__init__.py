from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "user.login"
bootstrap = Bootstrap()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    bootstrap.init_app(app)

    from app.routes.main_routes import main_bp

    app.register_blueprint(main_bp)

    from app.routes.user_routes import user_bp

    app.register_blueprint(user_bp, url_prefix="/user")

    from app.routes.course_routes import course_bp

    app.register_blueprint(course_bp, url_prefix="/course")

    from app.routes.recommendation_routes import recommendation_bp

    app.register_blueprint(recommendation_bp, url_prefix="/recommendation")

    from app.routes.knowledge_graph_routes import knowledge_graph_bp

    app.register_blueprint(knowledge_graph_bp, url_prefix="/knowledge-graph")

    return app
