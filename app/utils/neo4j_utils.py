from py2neo import Graph


def get_neo4j_graph(uri, user, password):
    """
    创建并返回一个连接到 Neo4j 数据库的 Graph 对象。

    :param uri: Neo4j 数据库的 URI
    :param user: 数据库用户名
    :param password: 数据库密码
    :return: py2neo.Graph 对象
    """
    return Graph(uri, auth=(user, password))


def run_query(graph, query, parameters=None):
    """
    在 Neo4j 数据库中执行 Cypher 查询。

    :param graph: py2neo.Graph 对象
    :param query: Cypher 查询语句
    :param parameters: 查询参数字典 (默认为 None)
    :return: 查询结果
    """
    return graph.run(query, parameters)


def create_node(graph, label, properties):
    """
    在 Neo4j 数据库中创建一个带有标签和属性的节点。

    :param graph: py2neo.Graph 对象
    :param label: 节点标签
    :param properties: 节点属性字典
    :return: 创建的节点
    """
    return graph.create(graph.node(label, **properties))


def create_relationship(graph, node1, node2, relationship_type, properties=None):
    """
    在 Neo4j 数据库中创建两个节点之间的关系。

    :param graph: py2neo.Graph 对象
    :param node1: 起始节点
    :param node2: 目标节点
    :param relationship_type: 关系类型
    :param properties: 关系属性字典 (默认为 None)
    :return: 创建的关系
    """
    if properties is None:
        properties = {}
    return graph.create(
        graph.relationships.create(relationship_type, node1, node2, **properties)
    )


def find_node(graph, label, properties):
    """
    在 Neo4j 数据库中查找具有指定标签和属性的节点。

    :param graph: py2neo.Graph 对象
    :param label: 节点标签
    :param properties: 节点属性字典
    :return: 匹配的节点列表
    """
    return graph.nodes.match(label, **properties).all()


def find_relationship(graph, node1, node2, relationship_type):
    """
    在 Neo4j 数据库中查找两个节点之间的指定类型的关系。

    :param graph: py2neo.Graph 对象
    :param node1: 起始节点
    :param node2: 目标节点
    :param relationship_type: 关系类型
    :return: 匹配的关系列表
    """
    return graph.relationships.match((node1, node2), r_type=relationship_type).all()
