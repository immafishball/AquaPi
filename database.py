from flask import g

import sqlite3
import time

DATABASE = "/home/pi/Projects/AquaPi/sensor_data.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


def create_tables():
    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def save_temp_data(timestamp, celsius, fahrenheit):
    db = get_db()
    db.execute(
        "INSERT INTO temperature_log (timestamp, celsius, fahrenheit) VALUES (?, ?, ?)",
        (timestamp, celsius, fahrenheit),
    )
    db.commit()


def get_last_hour_temperature_data():
    db = get_db()
    # Calculate the timestamp for one hour ago in milliseconds
    one_hour_ago = time.time() * 1000 - 3600 * 1000
    cursor = db.execute(
        "SELECT timestamp, celsius, fahrenheit FROM temperature_log WHERE timestamp >= ? ORDER BY timestamp ASC",
        (one_hour_ago,),
    )
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        # Extract only the values from each row
        data_list = [
            [row["timestamp"], row["celsius"], row["fahrenheit"]] for row in rows
        ]
        return data_list

    return None


def get_last_day_temperature_data():
    db = get_db()
    # Calculate the timestamp for one day ago in milliseconds
    one_day_ago = time.time() * 1000 - 24 * 3600 * 1000
    cursor = db.execute(
        'SELECT AVG(celsius) as avg_celsius, AVG(fahrenheit) as avg_fahrenheit, strftime("%Y-%m-%d %H:00:00", datetime(timestamp/1000, "unixepoch", "localtime")) as avg_timestamp FROM temperature_log WHERE timestamp >= ? GROUP BY strftime("%Y-%m-%d %H", datetime(timestamp/1000, "unixepoch", "localtime")) ORDER BY timestamp ASC',
        (one_day_ago,),
    )
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        # Extract only the values from each row
        data_list = [
            [row["avg_timestamp"], row["avg_celsius"], row["avg_fahrenheit"]]
            for row in rows
        ]
        return data_list

    return None
