import pytest

from app.services.topic_modeling_service import (
    TopicModelService,
    GENSIM_AVAILABLE,
)


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
