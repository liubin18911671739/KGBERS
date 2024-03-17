import unittest
from unittest.mock import MagicMock, patch
from app.models.knowledge_graph import KnowledgeGraph
from app.utils.neo4j_utils import get_neo4j_graph


class TestKnowledgeGraph(unittest.TestCase):

    def setUp(self):
        self.graph = get_neo4j_graph("bolt://localhost:7687", "neo4j", "password")
        self.knowledge_graph = KnowledgeGraph(self.graph)

    def test_create_concept(self):
        with patch.object(self.graph, "create") as mock_create:
            mock_node = MagicMock()
            mock_create.return_value = mock_node

            concept = self.knowledge_graph.create_concept(
                "Python", "Programming language"
            )

            mock_create.assert_called_once()
            self.assertEqual(concept, mock_node)

    def test_find_concept(self):
        with patch.object(self.graph.nodes, "match") as mock_match:
            mock_node = MagicMock()
            mock_match.return_value.first.return_value = mock_node

            concept = self.knowledge_graph.find_concept("Python")

            mock_match.assert_called_once_with("Concept", name="Python")
            self.assertEqual(concept, mock_node)

    def test_find_related_concepts(self):
        mock_concept = MagicMock()
        mock_concept.__getitem__.return_value = "Python"

        with patch.object(self.graph, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.data.return_value = [
                {"c2": {"name": "Flask"}},
                {"c2": {"name": "Django"}},
            ]
            mock_run.return_value = mock_result

            related_concepts = self.knowledge_graph.find_related_concepts(
                mock_concept, "RELATED_TO", 2
            )

            expected_query = """
                MATCH (c1:Concept {name: $concept_name})-[:RELATED_TO]-(c2:Concept)
                RETURN c2
                LIMIT 2
            """
            mock_run.assert_called_once_with(expected_query, concept_name="Python")
            self.assertEqual(related_concepts, [{"name": "Flask"}, {"name": "Django"}])

    def test_get_concept_graph(self):
        mock_concept = MagicMock()
        mock_concept.__getitem__.return_value = "Python"

        with patch.object(self.graph, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.data.return_value = [
                {"c": {"name": "Python"}, "related": {"name": "Flask"}},
                {"c": {"name": "Python"}, "related": {"name": "Django"}},
            ]
            mock_run.return_value = mock_result

            concept_graph = self.knowledge_graph.get_concept_graph(mock_concept, 2)

            expected_query = """
                MATCH (c:Concept {name: $concept_name})-[*1..2]-(related)
                RETURN c, related
            """
            mock_run.assert_called_once_with(expected_query, concept_name="Python")
            expected_nodes = [{"name": "Python"}, {"name": "Flask"}, {"name": "Django"}]
            expected_edges = [
                ({"name": "Python"}, {"name": "Flask"}),
                ({"name": "Python"}, {"name": "Django"}),
            ]
            self.assertEqual(concept_graph["nodes"], expected_nodes)
            self.assertEqual(concept_graph["edges"], expected_edges)


if __name__ == "__main__":
    unittest.main()
