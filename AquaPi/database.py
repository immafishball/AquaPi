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

def get_all_data():
    db = get_db()
    cursor = db.execute('''
        SELECT 
            p.timestamp AS timestamp, 
            p.ph AS ph, 
            p.status AS ph_status, 
            t.celsius AS temp_celsius, 
            t.fahrenheit AS temp_fahrenheit, 
            t.status AS temp_status, 
            u.turbidity AS turbidity, 
            u.status AS turbidity_status, 
            w.water_level AS water_level
        FROM ph_level_log p
        LEFT JOIN temperature_log t ON p.timestamp = t.timestamp
        LEFT JOIN turbidity_log u ON p.timestamp = u.timestamp
        LEFT JOIN water_level_log w ON p.timestamp = w.timestamp
        ORDER BY p.timestamp ASC
    ''')
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        data_list = [
            [
                row["timestamp"],
                row["ph"],
                row["ph_status"],
                row["temp_celsius"],
                row["temp_fahrenheit"],
                row["temp_status"],
                row["turbidity"],
                row["turbidity_status"],
                row["water_level"]
            ] for row in rows
        ]
        return data_list

    return None

def save_temp_data(timestamp, celsius, fahrenheit, status):
    db = get_db()
    db.execute(
        "INSERT INTO temperature_log (timestamp, celsius, fahrenheit, status) VALUES (?, ?, ?, ?)",
        (timestamp, celsius, fahrenheit, status),
    )
    db.commit()
        
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

def save_water_level_data(timestamp, water_level):
    db = get_db()
    db.execute(
        "INSERT INTO water_level_log (timestamp, water_level) VALUES (?, ?)",
        (timestamp, water_level),
    )
    db.commit()

def save_ph_level_data(timestamp, ph, status):
    db = get_db()
    db.execute(
        "INSERT INTO ph_level_log (timestamp, ph, status) VALUES (?, ?, ?)",
        (timestamp, ph, status),
    )
    db.commit()

def save_turbidity_data(timestamp, turbidity, status):
    db = get_db()
    db.execute(
        "INSERT INTO turbidity_log (timestamp, turbidity, status) VALUES (?, ?, ?)",
        (timestamp, turbidity, status),
    )
    db.commit()

def get_last_hour_water_level_data():
    db = get_db()
    one_hour_ago = time.time() * 1000 - 3600 * 1000
    cursor = db.execute(
        "SELECT timestamp, water_level FROM water_level_log WHERE timestamp >= ? ORDER BY timestamp ASC",
        (one_hour_ago,),
    )
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        # Extract only the values from each row
        data_list = [
            [row["timestamp"], row["water_level"]] for row in rows
        ]
        return data_list

    return None

def get_last_day_water_level_data():
    db = get_db()
    one_day_ago = time.time() * 1000 - 24 * 3600 * 1000
    cursor = db.execute(
        '''SELECT avg_timestamp, water_level
           FROM (
               SELECT strftime("%Y-%m-%d %H:00:00", datetime(timestamp/1000, "unixepoch", "localtime")) as avg_timestamp,
                      water_level,
                      COUNT(*) as count
               FROM water_level_log
               WHERE timestamp >= ?
               GROUP BY avg_timestamp, water_level
               ORDER BY count DESC
           ) as subquery
           GROUP BY avg_timestamp
           ORDER BY avg_timestamp ASC''',
        (one_day_ago,),
    )
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        # Extract only the values from each row
        data_list = [
            [row["avg_timestamp"], row["water_level"]] for row in rows
        ]
        return data_list

    return None

def get_last_hour_ph_level_data():
    db = get_db()
    one_hour_ago = time.time() * 1000 - 3600 * 1000
    cursor = db.execute(
        "SELECT timestamp, ph, status FROM ph_level_log WHERE timestamp >= ? ORDER BY timestamp ASC",
        (one_hour_ago,),
    )
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        # Extract only the values from each row
        data_list = [
            [row["timestamp"], row["ph"], row["status"]] for row in rows
        ]
        return data_list

    return None

def get_last_day_ph_level_data():
    db = get_db()
    one_day_ago = time.time() * 1000 - 24 * 3600 * 1000
    cursor = db.execute(
        '''SELECT AVG(ph) as avg_ph,
                   strftime("%Y-%m-%d %H:00:00", datetime(timestamp/1000, "unixepoch", "localtime")) as avg_timestamp 
           FROM ph_level_log 
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
            [row["avg_timestamp"], row["avg_ph"]] for row in rows
        ]
        return data_list

    return None

def get_last_hour_turbidity_data():
    db = get_db()
    one_hour_ago = time.time() * 1000 - 3600 * 1000
    cursor = db.execute(
        "SELECT timestamp, turbidity, status FROM turbidity_log WHERE timestamp >= ? ORDER BY timestamp ASC",
        (one_hour_ago,),
    )
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        # Extract only the values from each row
        data_list = [
            [row["timestamp"], row["turbidity"], row["status"]] for row in rows
        ]
        return data_list

    return None

def get_last_day_turbidity_data():
    db = get_db()
    one_day_ago = time.time() * 1000 - 24 * 3600 * 1000
    cursor = db.execute(
        '''SELECT avg_timestamp, turbidity, status
           FROM (
               SELECT strftime("%Y-%m-%d %H:00:00", datetime(timestamp/1000, "unixepoch", "localtime")) as avg_timestamp,
                      turbidity,
                      status,
                      COUNT(*) as count
               FROM turbidity_log
               WHERE timestamp >= ?
               GROUP BY avg_timestamp, turbidity, status
               ORDER BY count DESC
           ) as subquery
           GROUP BY avg_timestamp
           ORDER BY avg_timestamp ASC''',
        (one_day_ago,),
    )
    rows = cursor.fetchall()
    cursor.close()

    if rows:
        # Extract only the values from each row
        data_list = [
            [row["avg_timestamp"], row["turbidity"], row["status"]] for row in rows
        ]
        return data_list

    return None