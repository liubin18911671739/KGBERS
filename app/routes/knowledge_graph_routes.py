from flask import Blueprint, render_template, request, jsonify
from app.models.knowledge_graph import KnowledgeGraph
from app.utils.neo4j_utils import get_neo4j_db

knowledge_graph_bp = Blueprint("knowledge_graph", __name__)


@knowledge_graph_bp.route("/knowledge_graph")
def knowledge_graph():
    return render_template("knowledge_graph.html")


@knowledge_graph_bp.route("/knowledge_graph/concept", methods=["POST"])
def create_concept():
    name = request.json["name"]
    description = request.json["description"]

    neo4j_db = get_neo4j_db()
    kg = KnowledgeGraph(neo4j_db)
    concept = kg.create_concept(name, description)

    return jsonify(concept_id=concept.identity), 201


@knowledge_graph_bp.route("/knowledge_graph/concept/<name>")
def get_concept(name):
    neo4j_db = get_neo4j_db()
    kg = KnowledgeGraph(neo4j_db)
    concept = kg.find_concept(name)

    if concept:
        return jsonify(name=concept["name"], description=concept["description"])
    else:
        return jsonify(message="Concept not found"), 404


@knowledge_graph_bp.route("/knowledge_graph/concept/<name>/related")
def get_related_concepts(name):
    relation_type = request.args.get("relation_type", "RELATED_TO")
    limit = int(request.args.get("limit", 10))

    neo4j_db = get_neo4j_db()
    kg = KnowledgeGraph(neo4j_db)
    concept = kg.find_concept(name)

    if concept:
        related_concepts = kg.find_related_concepts(concept, relation_type, limit)
        return jsonify(related_concepts=[c["name"] for c in related_concepts])
    else:
        return jsonify(message="Concept not found"), 404


@knowledge_graph_bp.route("/knowledge_graph/concept/<name>/graph")
def get_concept_graph(name):
    depth = int(request.args.get("depth", 2))

    neo4j_db = get_neo4j_db()
    kg = KnowledgeGraph(neo4j_db)
    concept = kg.find_concept(name)

    if concept:
        concept_graph = kg.get_concept_graph(concept, depth)
        return jsonify(concept_graph)
    else:
        return jsonify(message="Concept not found"), 404
