import json
import os
import mysql.connector
from typing import Any
from dotenv import load_dotenv
from mysql.connector import Error
from models.attractions import Attraction

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "taipei_day_trip"),
}

IMG_HOST = os.getenv("IMG_HOST", "")


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def normalize_json_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, list):
        return value
    return []


def fetch_attraction_rows(sql: str, params: tuple[Any, ...] = ()) -> list[Attraction]:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [Attraction.from_row(row) for row in rows]
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


def get_attractions(
    category: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    per_page: int = 8,
) -> dict[str, Any]:
    page = max(page, 1)
    offset = (page - 1) * per_page

    where_clauses = []
    params: list[Any] = []

    if category:
        where_clauses.append("category = %s")
        params.append(category)

    if keyword:
        where_clauses.append("(JSON_CONTAINS(mrt, JSON_ARRAY(%s)) OR name LIKE %s)")
        params.append(keyword)
        params.append(f"%{keyword}%")

    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    sql = (
        "SELECT id, name, category, description, address, transport, mrt, latitude, longitude, images "
        "FROM attractions "
        f"{where_clause} "
        "ORDER BY id LIMIT %s OFFSET %s"
    )
    params.extend([per_page, offset])

    attractions = fetch_attraction_rows(sql, tuple(params))
    next_page = page + 1 if len(attractions) == per_page else None
    return {"data": [attraction.to_dict(IMG_HOST) for attraction in attractions], "nextPage": next_page}


def get_attraction(attraction_id: int) -> dict[str, Any] | None:
    sql = (
        "SELECT id, name, category, description, address, transport, mrt, latitude, longitude, images "
        "FROM attractions WHERE id = %s"
    )
    attractions = fetch_attraction_rows(sql, (attraction_id,))
    return attractions[0].to_dict(IMG_HOST) if attractions else None


def get_categories() -> dict[str, Any]:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM attractions WHERE category IS NOT NULL AND category <> '' ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        return {"data": categories}
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


def get_mrts() -> dict[str, Any]:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT mrt FROM attractions WHERE mrt IS NOT NULL")
        rows = cursor.fetchall()
        mrts = []
        for (value,) in rows:
            for item in normalize_json_field(value):
                if item not in mrts:
                    mrts.append(item)
        mrts.sort()
        return {"data": mrts}
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()
