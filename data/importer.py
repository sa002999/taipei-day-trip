import json
from pathlib import Path

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv()

DATA_PATH = Path(__file__).parent  / "taipei-attractions.json"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "taipei_day_trip"),
}


def normalize_images(imgurls):
    if not imgurls:
        return []
    return [f'{part}.jpg' for part in imgurls.split(".jpg") if part]


def normalize_mrt(value):
    if value is None:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def create_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS attractions (
            id INT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100),
            description TEXT,
            address VARCHAR(255),
            transport TEXT,
            mrt JSON,
            latitude DECIMAL(10, 7),
            longitude DECIMAL(10, 7),
            images JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def load_source_data():
    with DATA_PATH.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return payload.get("list", [])


def build_insert_data(item):
    return {
        "id": item.get("_id"),
        "name": item.get("name"),
        "category": item.get("CAT"),
        "description": item.get("description"),
        "address": item.get("address"),
        "transport": item.get("direction"),
        "mrt": json.dumps(normalize_mrt(item.get("MRT"))),
        "latitude": parse_float(item.get("latitude")),
        "longitude": parse_float(item.get("longitude")),
        "images": json.dumps(normalize_images(item.get("imgurls"))),
    }


def import_attractions():
    source_items = load_source_data()

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        create_table(cursor)

        insert_sql = """
            INSERT INTO attractions
                (id, name, category, description, address, transport, mrt, latitude, longitude, images)
            VALUES
                (%(id)s, %(name)s, %(category)s, %(description)s, %(address)s, %(transport)s, %(mrt)s, %(latitude)s, %(longitude)s, %(images)s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                category = VALUES(category),
                description = VALUES(description),
                address = VALUES(address),
                transport = VALUES(transport),
                mrt = VALUES(mrt),
                latitude = VALUES(latitude),
                longitude = VALUES(longitude),
                images = VALUES(images)
        """

        for item in source_items:
            record = build_insert_data(item)
            cursor.execute(insert_sql, record)

        conn.commit()
        print(f"Imported {cursor.rowcount} rows into attractions.")
    except Error as err:
        print("MySQL error:", err)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    import_attractions()