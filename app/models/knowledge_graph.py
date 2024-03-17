from py2neo import Graph, Node, Relationship


class KnowledgeGraph:
    def __init__(self, uri, user, password):
        self.graph = Graph(uri, auth=(user, password))

    def create_concept(self, name, description):
        concept = Node("Concept", name=name, description=description)
        self.graph.create(concept)
        return concept

    def create_relation(self, start_node, end_node, relation_type):
        relation = Relationship(start_node, relation_type, end_node)
        self.graph.create(relation)
        return relation

    def find_concept(self, name):
        concept = self.graph.nodes.match("Concept", name=name).first()
        return concept

    def find_related_concepts(self, concept, relation_type, limit=10):
        query = f"""
            MATCH (c1:Concept {{name: $concept_name}})-[:{relation_type}]-(c2:Concept)
            RETURN c2
            LIMIT {limit}
        """
        result = self.graph.run(query, concept_name=concept["name"]).data()
        related_concepts = [record["c2"] for record in result]
        return related_concepts

    def get_concept_graph(self, concept, depth=2):
        query = f"""
            MATCH (c:Concept {{name: $concept_name}})-[*1..{depth}]-(related)
            RETURN c, related
        """
        result = self.graph.run(query, concept_name=concept["name"]).data()
        nodes = set()
        edges = set()
        for record in result:
            nodes.add(record["c"])
            nodes.add(record["related"])
            edges.add((record["c"], record["related"]))
        return {"nodes": list(nodes), "edges": list(edges)}
