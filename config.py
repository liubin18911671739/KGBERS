import os


class Config:
    # Flask 应用配置
    SECRET_KEY = os.environ.get("SECRET_KEY") or "your-secret-key"

    # SQLite 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(
        os.path.dirname(__file__), "data", "sqlite", "app.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Neo4j 图数据库配置
    NEO4J_URI = os.environ.get("NEO4J_URI") or "neo4j://localhost:7687"
    NEO4J_USER = os.environ.get("NEO4J_USER") or "neo4j"
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD") or "your-neo4j-password"

    # 课程数据爬取配置
    COURSE_DATA_URLS = [
        "https://www.example.com/courses",
        # 添加更多课程数据源的 URL
    ]

    # 推荐系统参数配置
    RECOMMENDATION_TOP_N = 10
    RECOMMENDATION_ALGORITHM = "collaborative_filtering"

    # 其他配置项
    # ...


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL"
    ) or "sqlite:///" + os.path.join(
        os.path.dirname(__file__), "data", "sqlite", "test.db"
    )


class ProductionConfig(Config):
    pass


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
