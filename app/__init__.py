import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_bootstrap import Bootstrap
from config import config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "user.login"
bootstrap = Bootstrap()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    bootstrap.init_app(app)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

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

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(base_dir, "data", "sqlite"), exist_ok=True)
    with app.app_context():
        from app import models  # noqa: F401

        # 测试环境直接建表;开发/生产通过 `flask db upgrade` 应用迁移。
        if app.config.get("TESTING"):
            db.create_all()

    from app.commands import register_commands

    register_commands(app)

    # 测试环境关闭 CSRF,便于直接提交表单/JSON。
    if app.config.get("TESTING"):
        app.config["WTF_CSRF_ENABLED"] = False

    return app
