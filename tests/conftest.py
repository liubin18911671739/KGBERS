import os

os.environ.setdefault("FLASK_CONFIG", "testing")

import pytest

from app import create_app, db


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.drop_all()
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _disable_neo4j(monkeypatch):
    """避免测试访问真实 Neo4j;知识图谱相关测试自行 mock。"""
    import app.services.recommendation_service as recommendation_service

    def _raise():
        raise RuntimeError("Neo4j disabled in tests")

    monkeypatch.setattr(recommendation_service, "get_neo4j_db", _raise)
