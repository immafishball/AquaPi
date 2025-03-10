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
    read_operation_status,
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
    save_temp_data,
    save_water_level_data,
    save_ph_level_data,
    save_turbidity_data,
    save_operation_data,
    get_last_hour_temperature_data,
    get_last_day_temperature_data,
    get_last_hour_water_level_data,
    get_last_day_water_level_data,
    get_last_hour_ph_level_data,
    get_last_day_ph_level_data,
    get_last_hour_turbidity_data,
    get_last_day_turbidity_data,
    get_last_hour_operation_data,
    get_last_day_operation_data,
    get_all_data
)

import time
import sqlite3
import os
import atexit
import threading

from apscheduler.schedulers.background import BackgroundScheduler

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize APScheduler
scheduler = BackgroundScheduler()

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
    "operation": None,
}

def read_sensors():
    with app.app_context():
        while True:
            timestamp = time.time() * 1000  # Current timestamp
            
            _, celsius, fahrenheit, status = read_water_temperature(timestamp)
            if celsius is not None:
                sensor_data["temperature"] = (timestamp, celsius, fahrenheit, status)
            
            _, water_level = read_water_sensor(timestamp)
            if water_level is not None:
                sensor_data["water_level"] = (timestamp, water_level)

            _, ph, status = read_ph_level(timestamp)
            if ph is not None:
                sensor_data["ph"] = (timestamp, ph, status)

            _, turbidity, status = read_turbidity(timestamp)
            if turbidity is not None:
                sensor_data["turbidity"] = (timestamp, turbidity, status)

            _, operation, status = read_operation_status(timestamp)
            if operation is not None:
                sensor_data["operation"] = (timestamp, operation, status)

            time.sleep(1)  # Adjust sampling rate

def periodic_tasks():
    with app.app_context():
        while True:
            timestamp = time.time() * 1000  # Generate a single timestamp
            
            # Save temperature data
            _, celsius, fahrenheit, status = read_water_temperature(timestamp)
            if celsius is not None:
                save_temp_data(timestamp, celsius, fahrenheit, status)

            # Save water level data
            _, water_level = read_water_sensor(timestamp)
            if water_level is not None:
                save_water_level_data(timestamp, water_level)

            # Save pH level data
            _, ph, status = read_ph_level(timestamp)
            if ph is not None:
                save_ph_level_data(timestamp, ph, status)

            # Save turbidity data
            _, turbidity, status = read_turbidity(timestamp)
            if turbidity is not None:
                save_turbidity_data(timestamp, turbidity, status)
            
            # Save turbidity data
            _, operation, status = read_operation_status(timestamp)
            if operation is not None:
                save_operation_data(timestamp, operation, status)

            time.sleep(60)  # Sleep for 60 seconds

# Start the background thread for reading sensors
sensor_thread = threading.Thread(target=read_sensors, daemon=True)
periodic_thread = threading.Thread(target=periodic_tasks, daemon=True)

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
    return render_template("settings.html")

@app.route("/get_operation", methods=["GET"])
def get_operation():
    time_range = request.args.get("timeRange", "latest")

    if time_range == "latest":
        data = sensor_data["operation"]
    elif time_range == "lastHour":
        data = get_last_hour_operation_data()
    elif time_range == "lastDay":
        data = get_last_day_operation_data()
    else:
        return jsonify({"error": "Invalid time range"})

    if "data" in locals():
        return jsonify(data)
    elif celsius is not None:
        data = [timestamp, operation, status]
        return jsonify(data)
    return jsonify({"error": "Sensor not found"})

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
        data = [timestamp, water_level]
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
    data = get_all_data()
    if data:
        return jsonify(data)
    return jsonify({"error": "No data found"}), 404

if __name__ == "__main__":
    atexit.register(cleanup)  # Register cleanup function
    app.run(host="0.0.0.0", port=5000, threaded=True)
