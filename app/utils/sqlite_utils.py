import sqlite3


def get_db_connection(db_path):
    """
    创建并返回一个连接到 SQLite 数据库的 Connection 对象。

    :param db_path: SQLite 数据库文件路径
    :return: sqlite3.Connection 对象
    """
    conn = sqlite3.connect(db_path)
    return conn


def create_table(conn, table_name, columns):
    """
    在 SQLite 数据库中创建一个新表。

    :param conn: sqlite3.Connection 对象
    :param table_name: 表名
    :param columns: 列定义的字符串,例如 "id INTEGER PRIMARY KEY, name TEXT, age INTEGER"
    """
    cursor = conn.cursor()
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
    conn.commit()


def insert_data(conn, table_name, data):
    """
    向 SQLite 数据库表中插入数据。

    :param conn: sqlite3.Connection 对象
    :param table_name: 表名
    :param data: 要插入的数据列表,每个元素为一个元组,对应表中的一行数据
    """
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(data[0]))
    cursor.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", data)
    conn.commit()


def select_data(conn, table_name, columns="*", condition=None):
    """
    从 SQLite 数据库表中查询数据。

    :param conn: sqlite3.Connection 对象
    :param table_name: 表名
    :param columns: 要查询的列名,默认为 '*' 表示查询所有列
    :param condition: 查询条件,例如 "age > 18",默认为 None 表示无条件
    :return: 查询结果列表,每个元素为一个元组,对应一行数据
    """
    cursor = conn.cursor()
    query = f"SELECT {columns} FROM {table_name}"
    if condition:
        query += f" WHERE {condition}"
    cursor.execute(query)
    return cursor.fetchall()


def update_data(conn, table_name, update_fields, condition):
    """
    更新 SQLite 数据库表中的数据。

    :param conn: sqlite3.Connection 对象
    :param table_name: 表名
    :param update_fields: 要更新的字段和值,例如 "name = 'John', age = 20"
    :param condition: 更新条件,例如 "id = 1"
    """
    cursor = conn.cursor()
    query = f"UPDATE {table_name} SET {update_fields} WHERE {condition}"
    cursor.execute(query)
    conn.commit()


def delete_data(conn, table_name, condition):
    """
    从 SQLite 数据库表中删除数据。

    :param conn: sqlite3.Connection 对象
    :param table_name: 表名
    :param condition: 删除条件,例如 "age < 18"
    """
    cursor = conn.cursor()
    query = f"DELETE FROM {table_name} WHERE {condition}"
    cursor.execute(query)
    conn.commit()
