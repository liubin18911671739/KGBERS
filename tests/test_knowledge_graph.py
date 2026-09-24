from unittest.mock import MagicMock

from app.models.knowledge_graph import KnowledgeGraph


def _knowledge_graph():
    graph = MagicMock()
    return graph, KnowledgeGraph(graph)


def test_create_concept_returns_node():
    graph, kg = _knowledge_graph()

    node = kg.create_concept("Python", "Programming language")

    graph.create.assert_called_once()
    assert node["name"] == "Python"


def test_find_concept():
    graph, kg = _knowledge_graph()
    graph.nodes.match.return_value.first.return_value = {"name": "Python"}

    assert kg.find_concept("Python") == {"name": "Python"}
    graph.nodes.match.assert_called_once_with("Concept", name="Python")


def test_find_related_concepts():
    graph, kg = _knowledge_graph()
    graph.run.return_value.data.return_value = [
        {"c2": {"name": "Flask"}},
        {"c2": {"name": "Django"}},
    ]

    result = kg.find_related_concepts({"name": "Python"}, "RELATED_TO", 2)

    assert result == [
        {"id": "Flask", "name": "Flask", "description": None},
        {"id": "Django", "name": "Django", "description": None},
    ]
    query = graph.run.call_args.args[0]
    assert "RELATED_TO" in query
    assert "LIMIT 2" in query
    assert graph.run.call_args.kwargs == {"concept_name": "Python"}


def test_get_concept_graph():
    graph, kg = _knowledge_graph()
    graph.run.return_value.data.return_value = [
        {"c": {"name": "Python"}, "related": {"name": "Flask"}},
        {"c": {"name": "Python"}, "related": {"name": "Django"}},
    ]

    result = kg.get_concept_graph({"name": "Python"}, 2)

    assert {node["id"] for node in result["nodes"]} == {"Python", "Flask", "Django"}
    assert {"source": "Python", "target": "Flask"} in result["links"]
    assert {"source": "Python", "target": "Django"} in result["links"]


def test_get_full_graph():
    graph, kg = _knowledge_graph()
    graph.run.return_value.data.return_value = [
        {"c": {"name": "A"}, "d": {"name": "B"}}
    ]

    result = kg.get_full_graph(limit=5)

    assert result["nodes"] == [
        {"id": "A", "name": "A", "description": None},
        {"id": "B", "name": "B", "description": None},
    ]
    assert result["links"] == [{"source": "A", "target": "B"}]
