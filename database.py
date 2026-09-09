import json
import os
import secrets
from datetime import datetime
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


def create_member(name: str, email: str, password_hash: str) -> bool:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO members (name, email, password_hash) VALUES (%s, %s, %s)",
            (name, email, password_hash),
        )
        conn.commit()
        return True
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


def get_member_by_email(email: str) -> dict[str, Any] | None:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, email, password_hash FROM members WHERE email = %s",
            (email,),
        )
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


def get_member_by_id(member_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, email FROM members WHERE id = %s",
            (member_id,),
        )
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


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
    return {
        "data": [attraction.to_dict(IMG_HOST) for attraction in attractions],
        "nextPage": next_page,
    }


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
        cursor.execute(
            "SELECT DISTINCT category FROM attractions WHERE category IS NOT NULL AND category <> '' ORDER BY category"
        )
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


def get_booking_by_member(member_id: int) -> dict | None:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT b.member_id, b.attraction_id, b.date, b.time, b.price,
                   a.name, a.address, a.images
            FROM bookings b
            LEFT JOIN attractions a ON a.id = b.attraction_id
            WHERE b.member_id = %s
            """,
            (member_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        images = json.loads(row["images"]) if row.get("images") else []
        image_url = ""
        if images:
            path = images[0]
            base = IMG_HOST.rstrip("/")
            image_url = (
                f"{base}{path}"
                if base and path.startswith("/")
                else f"{base}/{path}" if base else path
            )

        return {
            "attraction": {
                "id": row["attraction_id"],
                "name": row["name"],
                "address": row["address"],
                "image": image_url,
            },
            "date": str(row["date"]),
            "time": row["time"],
            "price": int(row["price"]),
        }
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


def upsert_booking(
    member_id: int, attraction_id: int, date: str, time: str, price: int
) -> bool:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bookings (member_id, attraction_id, date, time, price)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                attraction_id = VALUES(attraction_id),
                date = VALUES(date),
                time = VALUES(time),
                price = VALUES(price),
                updated_at = CURRENT_TIMESTAMP
            """,
            (member_id, attraction_id, date, time, price),
        )
        conn.commit()
        return True
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


def delete_booking_by_member(member_id: int) -> bool:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE member_id = %s", (member_id,))
        conn.commit()
        return True
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


def create_order(
    member_id: int,
    booking: dict[str, Any],
    contact_name: str,
    contact_email: str,
    contact_phone: str,
) -> dict[str, Any]:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        order_number = (
            f"ORD{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(4).upper()}"
        )
        cursor.execute(
            """
            INSERT INTO orders (
                order_number, member_id, attraction_id, date, time, price,
                contact_name, contact_email, contact_phone, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'UNPAID')
            """,
            (
                order_number,
                member_id,
                booking["attraction"]["id"],
                booking["date"],
                booking["time"],
                booking["price"],
                contact_name,
                contact_email,
                contact_phone,
            ),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "order_number": order_number}
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


def update_order_status(order_id: int, status: str) -> bool:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE orders SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (status, order_id),
        )
        conn.commit()
        return cursor.rowcount == 1
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


def create_payment(order_id: int, amount: int, response: dict[str, Any]) -> bool:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO payments (
                order_id, status, message, amount, rec_trade_id,
                bank_transaction_id, tappay_order_number, response_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                order_id,
                int(response.get("status", -1)),
                str(response.get("msg", "付款失敗"))[:255],
                int(response.get("amount", amount) or amount),
                response.get("rec_trade_id"),
                response.get("bank_transaction_id"),
                response.get("order_number"),
                json.dumps(response, ensure_ascii=False),
            ),
        )
        conn.commit()
        return True
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()


def get_order_by_number(order_number: str, member_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT o.order_number, o.date, o.time, o.price, o.status,
                   o.contact_name, o.contact_email, o.contact_phone,
                     a.name AS attraction_name, a.address AS attraction_address,
                     a.images AS attraction_images
            FROM orders o
            LEFT JOIN attractions a ON a.id = o.attraction_id
            WHERE o.order_number = %s AND o.member_id = %s
            """,
            (order_number, member_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        images = normalize_json_field(row["attraction_images"])
        image_url = ""
        if images:
            path = images[0]
            base = IMG_HOST.rstrip("/")
            image_url = (
                f"{base}{path}"
                if base and path.startswith("/")
                else f"{base}/{path}" if base else path
            )

        return {
            "orderNumber": row["order_number"],
            "status": row["status"],
            "attraction": {
                "name": row["attraction_name"],
                "address": row["attraction_address"],
                "image": image_url,
            },
            "date": str(row["date"]),
            "time": row["time"],
            "price": int(row["price"]),
        }
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()
