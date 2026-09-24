from py2neo import Node, Relationship


class KnowledgeGraph:
    def __init__(self, graph):
        self.graph = graph

    def create_concept(self, name, description):
        concept = Node("Concept", name=name, description=description)
        self.graph.create(concept)
        return concept

    def create_relationship(self, start_node, end_node, relation_type):
        relation = Relationship(start_node, relation_type, end_node)
        self.graph.create(relation)
        return relation

    create_relation = create_relationship

    def find_concept(self, name):
        concept = self.graph.nodes.match("Concept", name=name).first()
        return concept

    def find_related_concepts(self, concept, relation_type, limit=10):
        query = (
            "MATCH (c1:Concept {name: $concept_name})-[:"
            f"{relation_type}]-(c2:Concept) RETURN c2 LIMIT {limit}"
        )
        result = self.graph.run(query, concept_name=concept["name"]).data()
        return [self._serialize_node(record["c2"]) for record in result]

    def get_concept_graph(self, concept, depth=2):
        query = (
            "MATCH (c:Concept {name: $concept_name})-[*1.."
            f"{depth}]-(related) RETURN c, related"
        )
        result = self.graph.run(query, concept_name=concept["name"]).data()
        return self._records_to_graph(result, "c", "related")

    def get_full_graph(self, limit=50):
        query = "MATCH (c:Concept)-[r]->(d:Concept) RETURN c, d LIMIT $limit"
        result = self.graph.run(query, limit=limit).data()
        return self._records_to_graph(result, "c", "d")

    @classmethod
    def _records_to_graph(cls, records, source_key, target_key):
        nodes = {}
        links = []
        for record in records:
            source = cls._serialize_node(record[source_key])
            target = cls._serialize_node(record[target_key])
            if source["id"] is not None:
                nodes[source["id"]] = source
            if target["id"] is not None:
                nodes[target["id"]] = target
            link = {"source": source["id"], "target": target["id"]}
            if link not in links:
                links.append(link)
        return {"nodes": list(nodes.values()), "links": links}

    @staticmethod
    def _serialize_node(value):
        data = value if isinstance(value, dict) else dict(value)
        name = data.get("name")
        return {
            "id": name,
            "name": name,
            "description": data.get("description"),
        }
