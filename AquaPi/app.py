from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    Response,
    g,
    send_from_directory,
)
from flask_cors import CORS
from importlib import import_module
from sensors import (
    read_water_temperature,
    read_water_sensor,
    read_turbidity,
    pump_water_on,
    pump_water_off,
    remove_water_off,
    remove_water_on,
    read_pump_status,
    read_ph_level,
    cleanup,
)
from feeder import feed_now, add_schedule, remove_schedule, get_schedules
from database import (
    get_db,
    create_tables,
    close_db,
    get_water_level_status_for_day,
    get_ph_level_status_for_day,
    get_dead_fish_detections,
    get_fish_change_events,
    save_temp_data,
    save_water_level_data,
    save_ph_level_data,
    save_turbidity_data,
    save_detected_objects,
    get_last_hour_temperature_data,
    get_last_day_temperature_data,
    get_last_hour_water_level_data,
    get_last_day_water_level_data,
    get_last_hour_ph_level_data,
    get_last_day_ph_level_data,
    get_last_hour_turbidity_data,
    get_last_day_turbidity_data,
    get_all_data
)

import time
import sqlite3
import os
import atexit
import threading
import logging

# Initialize Flask app
app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.disabled = True
CORS(app)

# import camera driver
if os.environ.get("CAMERA"):
    Camera = import_module("camera_" + os.environ["CAMERA"]).Camera
else:
    from camera import Camera

# Raspberry Pi camera module (requires picamera package)
# from camera_pi import Camera

sensor_data = {
    "temperature": None,
    "water_level": None,
    "ph": None,
    "turbidity": None,
    "detected_objects": None,
}

def read_sensors():
    with app.app_context():
        while True:
            # Get the current time in seconds
            current_time = int(time.time())

            # Force it to align with the previous full minute while keeping the seconds part
            fixed_timestamp = (current_time // 60) * 60 + (current_time % 60)

            # Convert to milliseconds
            timestamp = fixed_timestamp * 1000  # Ensures timestamp is a whole number
            
            _, celsius, fahrenheit, status = read_water_temperature(timestamp)
            if celsius is not None:
                sensor_data["temperature"] = (timestamp, celsius, fahrenheit, status)
                #print(f"[DEBUG] Updated temperature: {sensor_data['temperature']}")

            _, water_level, status = read_water_sensor(timestamp)
            if water_level is not None:
                sensor_data["water_level"] = (timestamp, water_level, status)
                #print(f"[DEBUG] Updated water level: {sensor_data['water_level']}")

            _, ph, status = read_ph_level(timestamp)
            if ph is not None:
                sensor_data["ph"] = (timestamp, ph, status)
                #print(f"[DEBUG] Updated pH: {sensor_data['ph']}")

            _, turbidity, status = read_turbidity(timestamp)
            if turbidity is not None:
                sensor_data["turbidity"] = (timestamp, turbidity, status)
                #print(f"[DEBUG] Updated turbidity: {sensor_data['turbidity']}")

            # If new detected objects are found, update them
            if Camera.detected_objects:
                sensor_data["detected_objects"] = (timestamp, Camera.detected_objects)
                #print(f"[DEBUG] Updated detected objects: {sensor_data['detected_objects']}")
                Camera.detected_objects = []  # Clear after storing
            #elif sensor_data["detected_objects"]:
                # Do not clear detected_objects; retain the last valid value
                #print("[DEBUG] No new detections, keeping previous detected objects.")

            time.sleep(1)  # Adjust sampling rate

def periodic_tasks():
    with app.app_context():
        while True:
            # Get the current time in seconds
            current_time = int(time.time())

            # Force it to align with the previous full minute while keeping the seconds part
            fixed_timestamp = (current_time // 60) * 60 + (current_time % 60)

            # Convert to milliseconds
            timestamp = fixed_timestamp * 1000  # Ensures timestamp is a whole number
            
            print(f"[DEBUG] Running periodic_tasks at {timestamp}")  # Debug log

            try:
                # Use sensor_data instead of calling functions again
                if sensor_data["temperature"] is not None:
                    ts, celsius, fahrenheit, status = sensor_data["temperature"]
                    save_temp_data(timestamp, celsius, fahrenheit, status)
                    print(f"[DEBUG] Temp Data Saved: {sensor_data['temperature']}")

                if sensor_data["water_level"] is not None:
                    ts, water_level, status = sensor_data["water_level"]
                    save_water_level_data(timestamp, water_level, status)
                    print(f"[DEBUG] Water Level Data Saved: {sensor_data['water_level']}")

                if sensor_data["ph"] is not None:
                    ts, ph, status = sensor_data["ph"]
                    save_ph_level_data(timestamp, ph, status)
                    print(f"[DEBUG] pH Data Saved: {sensor_data['ph']}")

                if sensor_data["turbidity"] is not None:
                    ts, turbidity, status = sensor_data["turbidity"]
                    save_turbidity_data(timestamp, turbidity, status)
                    print(f"[DEBUG] Turbidity Data Saved: {sensor_data['turbidity']}")

                if sensor_data["detected_objects"] is not None:
                    ts, detected_objects = sensor_data["detected_objects"]
                    save_detected_objects(timestamp, detected_objects)
                    print(f"[DEBUG] Detected Objects Saved: {sensor_data['detected_objects']}")

            except Exception as e:
                print(f"[ERROR] Database error: {e}")

            finally:
                close_db()  # Ensure the database connection is closed

            time.sleep(60)  # Sleep for 60 seconds

def start_periodic_tasks():
    while True:
        try:
            print("[DEBUG] Starting periodic_tasks() thread")
            periodic_tasks()
        except Exception as e:
            print(f"[ERROR] periodic_tasks crashed: {e}")
            time.sleep(5)

def start_read_sensors():
    while True:
        try:
            print("[DEBUG] Starting read_sensors() thread")
            read_sensors()
        except Exception as e:
            print(f"[ERROR] read_sensors crashed: {e}")
            time.sleep(5)

# Add debug logs before starting threads
print("[DEBUG] Starting sensor and periodic tasks threads...")

# Start the background thread for reading sensors
sensor_thread = threading.Thread(target=start_read_sensors, daemon=True)
periodic_thread = threading.Thread(target=start_periodic_tasks, daemon=True)

# Start the threads
sensor_thread.start()
periodic_thread.start()

# Add schedule to SQLite
@app.route("/add_schedule", methods=["POST"])
def add_schedule():
    try:
        content = request.get_json()
        time = content["time"]
        db = get_db()
        db.execute("INSERT INTO feeding_schedule (time) VALUES (?)", (time,))
        db.commit()
        return jsonify({"message": "Schedule added successfully"})
    except Exception as e:
        return jsonify({"error": str(e)})

# Get all schedules from SQLite
@app.route("/get_schedules", methods=["GET"])
def get_schedules():
    try:
        db = get_db()
        schedules = db.execute("SELECT * FROM feeding_schedule").fetchall()
        schedules_list = [{"id": row["id"], "time": row["time"]} for row in schedules]
        return jsonify(schedules_list)
    except Exception as e:
        return jsonify({"error": str(e)})

# Remove schedule from SQLite
@app.route("/remove_schedule", methods=["POST"])
def remove_schedule():
    try:
        content = request.get_json()
        schedule_id = content["id"]
        db = get_db()
        db.execute("DELETE FROM feeding_schedule WHERE id = ?", (schedule_id,))
        db.commit()
        return jsonify({"message": "Schedule removed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "aquarium-favicon.png",
        mimetype="image/vnd.microsoft.icon",
    )

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/camera")
def camera():
    return render_template("camera.html")

@app.route("/feeder")
def feeder():
    return render_template("feeder.html")

@app.route("/settings")
def settings():
    fish_type = request.args.get("fishType")
    return render_template("settings.html", fishType=fish_type)

@app.route("/get_temperature", methods=["GET"])
def get_temperature():
    time_range = request.args.get("timeRange", "latest")

    if time_range == "latest":
        data = sensor_data["temperature"]
    elif time_range == "lastHour":
        data = get_last_hour_temperature_data()
    elif time_range == "lastDay":
        data = get_last_day_temperature_data()
    else:
        return jsonify({"error": "Invalid time range"})

    if "data" in locals():
        return jsonify(data)
    elif celsius is not None:
        data = [timestamp, celsius, fahrenheit, status]
        return jsonify(data)
    return jsonify({"error": "Sensor not found"})

@app.route("/get_water_level", methods=["GET"])
def get_water_level():
    time_range = request.args.get("timeRange", "latest")

    if time_range == "latest":
        data = sensor_data["water_level"]
    elif time_range == "lastHour":
        data = get_last_hour_water_level_data()
    elif time_range == "lastDay":
        data = get_last_day_water_level_data()
    else:
        return jsonify({"error": "Invalid time range"})

    if "data" in locals():
        return jsonify(data)
    elif water_level is not None:
        data = [timestamp, water_level, status]
        return jsonify(data)
    return jsonify({"error": "Sensor not found"})

@app.route("/get_turbidity", methods=["GET"])
def get_turbidity():
    time_range = request.args.get("timeRange", "latest")

    if time_range == "latest":
        data = sensor_data["turbidity"]
    elif time_range == "lastHour":
        data = get_last_hour_turbidity_data()
    elif time_range == "lastDay":
        data = get_last_day_turbidity_data()
    else:
        return jsonify({"error": "Invalid time range"})

    if "data" in locals():
        return jsonify(data)
    elif turbidity is not None:
        data = [timestamp, turbidity, status]
        return jsonify(data)
    return jsonify({"error": "Sensor not found"})

@app.route("/get_ph_level", methods=["GET"])
def get_ph_level():
    time_range = request.args.get("timeRange", "latest")

    if time_range == "latest":
        data = sensor_data["ph"]
    elif time_range == "lastHour":
        data = get_last_hour_ph_level_data()
    elif time_range == "lastDay":
        data = get_last_day_ph_level_data()
    else:
        return jsonify({"error": "Invalid time range"})

    if "data" in locals():
        return jsonify(data)
    elif ph is not None:
        data = [timestamp, ph, status]
        return jsonify(data)
    return jsonify({"error": "Sensor not found"})

@app.route("/pump_status", methods=["GET"])
def get_pump_status():
    try:
        pump_number = request.args.get("pump_number", type=int)

        if pump_number not in [1, 2]:
            return jsonify({"error": "Invalid pump number"}), 400

        pump_status = read_pump_status(pump_number)
        return jsonify({"status": pump_status})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/feed_now", methods=["POST"])
def servo_control():
    try:
        feed_now()
        return jsonify({"message": "Feeding successful"})
    except Exception as e:
        return jsonify({"error": str(e)})

def gen(camera):
    """Video streaming generator function."""
    yield b"--frame\r\n"
    while True:
        frame = camera.get_frame()
        yield b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n--frame\r\n"

@app.route("/video_feed")
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/detect_objects", methods=["GET"])
def detect_objects():
    detected_objects = Camera.detected_objects
    Camera.detected_objects = []  # Clear the list after retrieving
    return jsonify(detected_objects)

@app.route("/get_all_data", methods=["GET"])
def get_all_data_endpoint():
    fish_type = request.args.get("fishType")  # Get the fishType parameter from the request
    data = get_all_data(fish_type)  # Pass it to the function

    if data:
        return jsonify(data)
    return jsonify({"error": "No data found"}), 404

@app.route("/get_water_level_now", methods=["GET"])
def get_water_level_now_endpoint():
    data = get_water_level_status_for_day()
    if data:
        return jsonify(data)
    return jsonify({"error": "No data found"}), 404

@app.route("/get_ph_level_now", methods=["GET"])
def get_ph_level_now_endpoint():
    data = get_ph_level_status_for_day()
    if data:
        return jsonify(data)
    return jsonify({"error": "No data found"}), 404

@app.route("/get_combined_status", methods=["GET"])
def get_combined_status():
    # Fetch data from both endpoints
    water_level_data = get_water_level_status_for_day()
    ph_level_data = get_ph_level_status_for_day()

    # Combine the data into a single response
    combined_data = {
        "water_level": water_level_data if water_level_data else [],
        "ph_level": ph_level_data if ph_level_data else []
    }

    # Return combined data
    return jsonify(combined_data)

@app.route("/get_dead_fish", methods=["GET"])
def get_dead_fish():
    return jsonify(get_dead_fish_detections())

@app.route("/get_fish_changes", methods=["GET"])
def get_fish_changes():
    try:
        fish_changes = get_fish_change_events()
        return jsonify(fish_changes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    atexit.register(cleanup)  # Register cleanup function
    app.run(host="0.0.0.0", port=5000, threaded=True)
