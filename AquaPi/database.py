from flask import g

import sqlite3
import time
import os

current_dir = os.getcwd()

DATABASE = '/home/pi/Projects/AquaPi/sensor_data.db'

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


def save_temp_data(timestamp, celsius, fahrenheit, status):
    db = get_db()
    db.execute(
        "INSERT INTO temperature_log (timestamp, celsius, fahrenheit, status) VALUES (?, ?, ?, ?)",
        (timestamp, celsius, fahrenheit, status),
    )
    db.commit()

def get_fish_data_by_name(fish_name):
    try:
        db = get_db()
        query = "SELECT * FROM Fish_Data WHERE name = ?"
        fish_data = db.execute(query, (fish_name,)).fetchone()

        if fish_data:
            result = {
                "name": fish_data["name"],
                "temp_min": fish_data["temp_min"],
                "temp_max": fish_data["temp_max"],
                "ph_min": fish_data["ph_min"],
                "ph_max": fish_data["ph_max"],
                "oxygen_min": fish_data["oxygen_min"],
                "oxygen_max": fish_data["oxygen_max"],
            }
            return result
        else:
            return None

    except Exception as e:
        print("Error fetching fish data:", e)
        return None

def update_fish_data(fish_name, temp_min, temp_max, ph_min, ph_max, oxygen_min, oxygen_max):
    try:
        db = get_db()
        db.execute(
            """
            UPDATE fish_data
            SET temp_min = ?, temp_max = ?, ph_min = ?, ph_max = ?, oxygen_min = ?, oxygen_max = ?
            WHERE name = ?
            """,
            (temp_min, temp_max, ph_min, ph_max, oxygen_min, oxygen_max, fish_name),
        )
        db.commit()
        return {"message": "Fish data updated successfully"}
    except Exception as e:
        return {"error": str(e)}
        
def get_last_hour_temperature_data():
    db = get_db()
    # Calculate the timestamp for one hour ago in milliseconds
    one_hour_ago = time.time() * 1000 - 3600 * 1000
    cursor = db.execute(
        "SELECT timestamp, celsius, fahrenheit, status FROM temperature_log WHERE timestamp >= ? ORDER BY timestamp ASC",
        (one_hour_ago,),
    )
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        # Extract only the values from each row
        data_list = [
            [row["timestamp"], row["celsius"], row["fahrenheit"], row["status"]] for row in rows
        ]
        return data_list

    return None


def get_last_day_temperature_data():
    db = get_db()
    # Calculate the timestamp for one day ago in milliseconds
    one_day_ago = time.time() * 1000 - 24 * 3600 * 1000
    cursor = db.execute(
        '''SELECT AVG(celsius) as avg_celsius, AVG(fahrenheit) as avg_fahrenheit, 
                  MAX(status) as status,  -- Get the most recent status
                  strftime("%Y-%m-%d %H:00:00", datetime(timestamp/1000, "unixepoch", "localtime")) as avg_timestamp 
           FROM temperature_log 
           WHERE timestamp >= ? 
           GROUP BY strftime("%Y-%m-%d %H", datetime(timestamp/1000, "unixepoch", "localtime")) 
           ORDER BY timestamp ASC''',
        (one_day_ago,),
    )
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        # Extract only the values from each row
        data_list = [
            [row["avg_timestamp"], row["avg_celsius"], row["avg_fahrenheit"], row["status"]] for row in rows
        ]
        return data_list

    return None
