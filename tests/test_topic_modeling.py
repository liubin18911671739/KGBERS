import re

import pytest

from app.services.topic_modeling_service import (
    TopicModelService,
    GENSIM_AVAILABLE,
    JIEBA_AVAILABLE,
    SKLEARN_AVAILABLE,
)


def _is_clean_token(token):
    return bool(re.fullmatch(r"[a-z0-9]+|[\u4e00-\u9fff]+", token))


def test_frequency_fallback_extracts_keywords():
    service = TopicModelService()

    topics = service.frequency_keywords(
        "Python Programming python algorithms", top_n=2
    )

    assert topics == ["python", "algorithms"]


def test_extract_without_fit_uses_fallback():
    service = TopicModelService()

    topics = service.extract("Machine Learning machine learning models", top_n=2)

    assert "machine" in topics
    assert len(topics) == 2


def test_fit_requires_enough_documents():
    service = TopicModelService()
    assert service.fit(["only one document"]) is False


def test_extract_handles_empty_text():
    service = TopicModelService()
    assert service.extract("") == []


@pytest.mark.skipif(not GENSIM_AVAILABLE, reason="gensim not installed")
def test_lda_topics_after_fit():
    service = TopicModelService(num_topics=2, top_n=2)
    documents = [
        "python programming variables functions loops",
        "python data structures algorithms complexity",
        "machine learning models training evaluation",
        "machine learning neural networks regression",
    ]

    assert service.fit(documents) is True
    topics = service.extract("python algorithms and data structures", top_n=2)

    assert len(topics) == 2


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_sklearn_backend_fits_and_extracts():
    service = TopicModelService(num_topics=2, top_n=2)
    documents = [
        "python programming variables functions loops",
        "python data structures algorithms complexity",
        "machine learning models training evaluation",
        "machine learning neural networks regression",
    ]

    assert service.fit(documents) is True
    assert service._sk_lda is not None
    topics = service.extract("machine learning neural networks", top_n=2)

    assert len(topics) == 2
    assert all(topic for topic in topics)


def test_backend_forced_frequency_disables_lda():
    """强制 frequency 后端时不训练任何 LDA,即使 sklearn/gensim 可用。"""
    service = TopicModelService(backend="frequency")
    documents = [
        "python programming variables functions loops",
        "python data structures algorithms complexity",
    ]

    assert service.fit(documents) is False
    assert service._sk_lda is None and service.lda is None
    topics = service.extract("python programming loops", top_n=3)
    assert set(topics) == {"python", "programming", "loops"}


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_backend_forced_sklearn_used_even_when_gensim_missing_or_present(monkeypatch):
    """强制 sklearn 时,即使 gensim 可用也使用 sklearn 后端。"""
    from app.services import topic_modeling_service as tms

    monkeypatch.setattr(tms, "GENSIM_AVAILABLE", False)
    service = tms.TopicModelService(backend="sklearn", num_topics=2, top_n=2)
    documents = [
        "python programming variables functions loops",
        "python data structures algorithms complexity",
        "machine learning models training evaluation",
        "machine learning neural networks regression",
    ]

    assert service.fit(documents) is True
    assert service.lda is None and service._sk_lda is not None


@pytest.mark.skipif(
    not (SKLEARN_AVAILABLE or GENSIM_AVAILABLE),
    reason="no LDA backend installed",
)
def test_auto_backend_picks_some_lda():
    service = TopicModelService(num_topics=2, top_n=2)
    documents = [
        "python programming variables functions loops",
        "python data structures algorithms complexity",
        "machine learning models training evaluation",
        "machine learning neural networks regression",
    ]

    assert service.fit(documents) is True
    assert (service.lda is not None) or (service._sk_lda is not None)


@pytest.mark.skipif(not JIEBA_AVAILABLE, reason="jieba not installed")
def test_jieba_tokenizes_chinese():
    service = TopicModelService()
    tokens = service.tokenize("机器学习基础课程")

    assert "机器学习" in tokens or "学习" in tokens
    assert all(_is_clean_token(token) for token in tokens)
