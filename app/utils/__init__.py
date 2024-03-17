from app.utils import get_neo4j_graph

graph = get_neo4j_graph("neo4j://localhost:7687", "neo4j", "password")
