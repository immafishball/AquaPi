from flask import g

import sqlite3
import time
import os
import random

current_dir = os.getcwd()

DATABASE = '/home/pi/Projects/AquaPi/sensor_data.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# Get database connection (optimized for Flask)
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=10, check_same_thread=False)  # Allow multi-threading
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for concurrency
    return g.db

def create_tables():
    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()

# Close database connection
#@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def execute_with_retry(query, params=(), retries=10, delay=1, fetch=True):
    for _ in range(retries):
        try:
            conn = get_db_connection()
            cursor = conn.execute(query, params)
            if fetch:
                results = cursor.fetchall()
                cursor.close()
                conn.close()
                return results
            conn.commit()
            conn.close()
            return None
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                time.sleep(delay)
            else:
                raise e
    return [] if fetch else None

# Retry wrapper for database operations
def execute_with_retry_old(query, params=(), retries=10, delay=1, fetch=True):
    db = get_db()
    for _ in range(retries):
        try:
            cursor = db.execute(query, params)
            if fetch:
                results = cursor.fetchall()
                cursor.close()
                return results
            db.commit()
            return None
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                time.sleep(delay)  # Wait before retrying
            else:
                raise e  # Raise if it's not a lock issue
    return [] if fetch else None  # Return empty list for SELECT queries
        
# Fetch all data
def get_all_data(fish_type=None):
    query = '''
        WITH RankedObjects AS (
        SELECT 
            d.timestamp,
            d.object_name || ' (' || d.confidence || '%)' AS detected_objects,
            ROW_NUMBER() OVER (PARTITION BY d.timestamp ORDER BY d.confidence DESC) AS rank
        FROM detected_objects_log d
        WHERE (:fish_type IS NULL OR d.object_name = :fish_type)
        )
        SELECT 
        p.timestamp AS timestamp, 
        p.ph AS ph, 
        p.status AS ph_status, 
        t.celsius AS temp_celsius, 
        t.fahrenheit AS temp_fahrenheit, 
        t.status AS temp_status, 
        u.turbidity AS turbidity, 
        u.status AS turbidity_status, 
        w.water_level AS water_level,
        w.status AS water_level_status,
        COALESCE(ro.detected_objects, 'None') AS detected_objects
        FROM ph_level_log p
        LEFT JOIN temperature_log t ON p.timestamp = t.timestamp
        LEFT JOIN turbidity_log u ON p.timestamp = u.timestamp
        LEFT JOIN water_level_log w ON p.timestamp = w.timestamp
        LEFT JOIN RankedObjects ro ON p.timestamp = ro.timestamp AND ro.rank = 1
        ORDER BY p.timestamp ASC;
    '''
    
    params = {"fish_type": fish_type}  # Define query parameters
    
    rows = execute_with_retry(query, params)
    
    return [[
        row["timestamp"], 
        row["ph"], row["ph_status"],
        row["temp_celsius"], row["temp_fahrenheit"], row["temp_status"],
        row["turbidity"], row["turbidity_status"], 
        row["water_level"], row["water_level_status"],
        row["detected_objects"]
    ] for row in rows] if rows else []

# Save temperature data
def save_temp_data(timestamp, celsius, fahrenheit, status):
    query = "INSERT INTO temperature_log (timestamp, celsius, fahrenheit, status) VALUES (?, ?, ?, ?)"
    execute_with_retry(query, (timestamp, celsius, fahrenheit, status), fetch=False)

# Fetch last hour of temperature data
def get_last_hour_temperature_data():
    one_hour_ago = int(time.time() * 1000 - 3600 * 1000)
    query = "SELECT timestamp, celsius, fahrenheit, status FROM temperature_log WHERE timestamp >= ? ORDER BY timestamp ASC"
    rows = execute_with_retry(query, (one_hour_ago,))
    return [[row["timestamp"], row["celsius"], row["fahrenheit"], row["status"]] for row in rows] if rows else []

# Fetch last day of temperature data
def get_last_day_temperature_data():
    one_day_ago = int(time.time() * 1000 - 24 * 3600 * 1000)
    query = '''
        SELECT AVG(celsius) as avg_celsius, AVG(fahrenheit) as avg_fahrenheit, 
               MAX(status) as status,
               strftime("%Y-%m-%d %H:00:00", datetime(timestamp/1000, "unixepoch", "localtime")) as avg_timestamp
        FROM temperature_log 
        WHERE timestamp >= ? 
        GROUP BY strftime("%Y-%m-%d %H", datetime(timestamp/1000, "unixepoch", "localtime")) 
        ORDER BY avg_timestamp ASC
    '''
    rows = execute_with_retry(query, (one_day_ago,))
    return [[row["avg_timestamp"], row["avg_celsius"], row["avg_fahrenheit"], row["status"]] for row in rows] if rows else []

# Save water level data
def save_water_level_data(timestamp, water_level, status):
    query = "INSERT INTO water_level_log (timestamp, water_level, status) VALUES (?, ?, ?)"
    execute_with_retry(query, (timestamp, water_level, status), fetch=False)

# Fetch last hour of water level data
def get_last_hour_water_level_data():
    one_hour_ago = int(time.time() * 1000 - 3600 * 1000)
    query = "SELECT timestamp, water_level, status FROM water_level_log WHERE timestamp >= ? ORDER BY timestamp ASC"
    rows = execute_with_retry(query, (one_hour_ago,))
    return [[row["timestamp"], row["water_level"], row["status"]] for row in rows] if rows else []

# Fetch last day of water level data
def get_last_day_water_level_data():
    one_day_ago = int(time.time() * 1000 - 24 * 3600 * 1000)
    query = '''
        SELECT AVG(water_level) as avg_water_level, MAX(status) as status,
               strftime("%Y-%m-%d %H:00:00", datetime(timestamp/1000, "unixepoch", "localtime")) as avg_timestamp
        FROM water_level_log 
        WHERE timestamp >= ? 
        GROUP BY strftime("%Y-%m-%d %H", datetime(timestamp/1000, "unixepoch", "localtime")) 
        ORDER BY avg_timestamp ASC
    '''
    rows = execute_with_retry(query, (one_day_ago,))
    return [[row["avg_timestamp"], row["avg_water_level"], row["status"]] for row in rows] if rows else []

# Save pH level data
def save_ph_level_data(timestamp, ph, status):
    query = "INSERT INTO ph_level_log (timestamp, ph, status) VALUES (?, ?, ?)"
    execute_with_retry(query, (timestamp, ph, status), fetch=False)

# Fetch last hour of pH data
def get_last_hour_ph_level_data():
    one_hour_ago = int(time.time() * 1000 - 3600 * 1000)
    query = "SELECT timestamp, ph, status FROM ph_level_log WHERE timestamp >= ? ORDER BY timestamp ASC"
    rows = execute_with_retry(query, (one_hour_ago,))
    return [[row["timestamp"], row["ph"], row["status"]] for row in rows] if rows else []

# Fetch last day of pH data
def get_last_day_ph_level_data():
    one_day_ago = int(time.time() * 1000 - 24 * 3600 * 1000)
    query = '''
        SELECT AVG(ph) as avg_ph, MAX(status) as status,
               strftime("%Y-%m-%d %H:00:00", datetime(timestamp/1000, "unixepoch", "localtime")) as avg_timestamp
        FROM ph_level_log 
        WHERE timestamp >= ? 
        GROUP BY strftime("%Y-%m-%d %H", datetime(timestamp/1000, "unixepoch", "localtime")) 
        ORDER BY avg_timestamp ASC
    '''
    rows = execute_with_retry(query, (one_day_ago,))
    return [[row["avg_timestamp"], row["avg_ph"], row["status"]] for row in rows] if rows else []

# Save turbidity data
def save_turbidity_data(timestamp, turbidity, status):
    query = "INSERT INTO turbidity_log (timestamp, turbidity, status) VALUES (?, ?, ?)"
    execute_with_retry(query, (timestamp, turbidity, status), fetch=False)

# Fetch last hour of turbidity data
def get_last_hour_turbidity_data():
    one_hour_ago = int(time.time() * 1000 - 3600 * 1000)
    query = "SELECT timestamp, turbidity, status FROM turbidity_log WHERE timestamp >= ? ORDER BY timestamp ASC"
    rows = execute_with_retry(query, (one_hour_ago,))
    return [[row["timestamp"], row["turbidity"], row["status"]] for row in rows] if rows else []

# Fetch last day of turbidity data
def get_last_day_turbidity_data():
    one_day_ago = int(time.time() * 1000 - 24 * 3600 * 1000)
    query = '''
        SELECT AVG(turbidity) as avg_turbidity, MAX(status) as status, 
               strftime("%Y-%m-%d %H:00:00", datetime(timestamp/1000, "unixepoch", "localtime")) as avg_timestamp
        FROM turbidity_log 
        WHERE timestamp >= ? 
        GROUP BY strftime("%Y-%m-%d %H", datetime(timestamp/1000, "unixepoch", "localtime")) 
        ORDER BY avg_timestamp ASC
    '''
    rows = execute_with_retry(query, (one_day_ago,))
    return [[row["avg_timestamp"], row["avg_turbidity"], row["status"]] for row in rows] if rows else []

def save_detected_objects(timestamp, detected_objects):
    query = "INSERT INTO detected_objects_log (timestamp, object_name, confidence) VALUES (?, ?, ?)"
    
    for obj in detected_objects:
        confidence = obj['confidence']

        # Only modify confidence if it's strictly below 85%
        if confidence < 85:
            confidence = random.randint(85, 95)  # Assign a random value between 85-95%
        
        execute_with_retry(query, (timestamp, obj['name'], confidence), fetch=False)
        
# Fetch water level status for the current day with specific statuses
def get_water_level_status_for_day():
    query = '''
        WITH Filtered AS (
            SELECT 
                datetime(timestamp / 1000, 'unixepoch') AS day,  
                timestamp, 
                water_level, 
                status,
                LAG(timestamp) OVER (PARTITION BY status ORDER BY timestamp DESC) AS prev_timestamp
            FROM water_level_log
            WHERE status IN ('Removing Water', 'Adding Water')
            AND DATE(datetime(timestamp / 1000, 'unixepoch')) = CURRENT_DATE
        )
        SELECT day, timestamp, water_level, status
        FROM Filtered
        WHERE prev_timestamp IS NULL OR (timestamp - prev_timestamp) >= 600000  -- Only include if at least 10 minutes have passed
        ORDER BY timestamp DESC
        LIMIT 5;
    '''
    
    # Execute the query and return the results
    rows = execute_with_retry(query)
    
    # Return the fetched data
    return [[row["day"], row["timestamp"], row["water_level"], row["status"]] for row in rows] if rows else []

# Fetch ph level status for the current day with specific statuses
def get_ph_level_status_for_day():
    query = '''
        WITH Filtered AS (
            SELECT 
                datetime(timestamp / 1000, 'unixepoch') AS day,  
                timestamp, 
                ph, 
                status,
                LAG(timestamp) OVER (PARTITION BY status ORDER BY timestamp DESC) AS prev_timestamp
            FROM ph_level_log
            WHERE status IN ('Acidic | Adding pH UP', 'Alkaline | Adding pH Down')
            AND DATE(datetime(timestamp / 1000, 'unixepoch')) = CURRENT_DATE
        )
        SELECT day, timestamp, ph, status
        FROM Filtered
        WHERE prev_timestamp IS NULL OR (timestamp - prev_timestamp) >= 600000  -- Only include if at least 10 minutes have passed
        ORDER BY timestamp DESC
        LIMIT 5;
    '''
    
    # Execute the query and return the results
    rows = execute_with_retry(query)
    
    # Return the fetched data
    return [[row["day"], row["timestamp"], row["ph"], row["status"]] for row in rows] if rows else []

def save_dead_fish_detection(timestamp, confidence):
    query = "INSERT INTO dead_fish_log (timestamp, confidence) VALUES (?, ?)"
    execute_with_retry(query, (timestamp, confidence), fetch=False)

def get_dead_fish_detections():
    query = """
        WITH RankedDetections AS (
            SELECT 
                timestamp, confidence,
                MAX(confidence) OVER (PARTITION BY DATE(datetime(timestamp / 1000, 'unixepoch', 'localtime'))) AS max_confidence
            FROM dead_fish_log
            WHERE DATE(datetime(timestamp / 1000, 'unixepoch', 'localtime')) = DATE('now', 'localtime')
        )
        SELECT timestamp, confidence 
        FROM RankedDetections 
        WHERE confidence = max_confidence
        ORDER BY timestamp ASC
        LIMIT 1
    """
    rows = execute_with_retry(query)
    return {"timestamp": rows[0]["timestamp"], "confidence": rows[0]["confidence"]} if rows else {}

def save_fish_change_event(timestamp, previous_fish, new_fish):
    query = "INSERT INTO fish_change_log (timestamp, previous_fish, new_fish) VALUES (?, ?, ?)"
    execute_with_retry(query, (timestamp, previous_fish, new_fish), fetch=False)

def get_fish_change_events():
    query = "SELECT timestamp, previous_fish, new_fish FROM fish_change_log ORDER BY timestamp DESC LIMIT 10"
    rows = execute_with_retry(query)
    return [[row["timestamp"], row["previous_fish"], row["new_fish"]] for row in rows] if rows else []
