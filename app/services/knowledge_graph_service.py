from app.models.knowledge_graph import KnowledgeGraph
from app.utils.neo4j_utils import get_neo4j_db


class KnowledgeService:
    def create_concept(name, description):
        neo4j_db = get_neo4j_db()
        kg = KnowledgeGraph(neo4j_db)
        concept = kg.create_concept(name, description)
        return concept

    def get_concept(name):
        neo4j_db = get_neo4j_db()
        kg = KnowledgeGraph(neo4j_db)
        concept = kg.find_concept(name)
        return concept

    def get_related_concepts(name, relation_type, limit):
        neo4j_db = get_neo4j_db()
        kg = KnowledgeGraph(neo4j_db)
        concept = kg.find_concept(name)

        if concept:
            related_concepts = kg.find_related_concepts(concept, relation_type, limit)
            return related_concepts
        else:
            return None

    def get_concept_graph(name, depth):
        neo4j_db = get_neo4j_db()
        kg = KnowledgeGraph(neo4j_db)
        concept = kg.find_concept(name)

        if concept:
            concept_graph = kg.get_concept_graph(concept, depth)
            return concept_graph
        else:
            return None

    def create_relation(start_node_name, end_node_name, relation_type):
        neo4j_db = get_neo4j_db()
        kg = KnowledgeGraph(neo4j_db)
        start_node = kg.find_concept(start_node_name)
        end_node = kg.find_concept(end_node_name)

        if start_node and end_node:
            relation = kg.create_relation(start_node, end_node, relation_type)
            return relation
        else:
            return None
