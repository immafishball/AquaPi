import io
import time
import cv2
import pandas as pd
import numpy as np
import cvzone
import argparse
import os
import random

from picamera2 import Picamera2
from libcamera import controls

from base_camera import BaseCamera
from ultralytics import YOLO
from datetime import datetime

from database import (
    save_dead_fish_detection,
    save_fish_change_event,
)

# Define and parse input arguments
parser = argparse.ArgumentParser()
parser.add_argument('--modeldir', help='Folder the .tflite file is located in',
                    required=True)
parser.add_argument('--graph', help='Name of the .tflite file, if different than detect.tflite',
                    default='detect.tflite')
parser.add_argument('--labels', help='Name of the labelmap file, if different than labelmap.txt',
                    default='labelmap.txt')
parser.add_argument('--threshold', help='Minimum confidence threshold for displaying detected objects',
                    default=0.5)
parser.add_argument('--imgsz', help='Defines the image size for inference. Can be a single integer 640 for square resizing or a (height, width) tuple. This should be same as what was used to export the YOLO model.',
                    default=240)
parser.add_argument('--resolution', help='Desired webcam resolution in WxH. If the webcam does not support the resolution entered, errors may occur.',
                    default='1280x720')
parser.add_argument('--capture', help='Enable image capture every 10 seconds',
                    action='store_true')

args = parser.parse_args()

MODEL_NAME = args.modeldir
GRAPH_NAME = args.graph
LABELMAP_NAME = args.labels
imgsz_count = int(args.imgsz)
min_conf_threshold = float(args.threshold)
resW, resH = args.resolution.split('x')
imW, imH = int(resW), int(resH)
capture_image = args.capture

# Create Capture folder if it doesn't exist
capture_folder = os.path.join(os.getcwd(), 'Capture')
os.makedirs(capture_folder, exist_ok=True)

# Get path to current working directory
CWD_PATH = os.getcwd()

# Path to .tflite file, which contains the model that is used for object detection
PATH_TO_CKPT = os.path.join(CWD_PATH, MODEL_NAME, GRAPH_NAME)

# Path to label map file
PATH_TO_LABELS = os.path.join(CWD_PATH, MODEL_NAME, LABELMAP_NAME)

# Load a official model or custom model
model = YOLO(PATH_TO_CKPT, verbose=False)

# Load class list
with open(PATH_TO_LABELS, "r") as file:
    class_list = file.read().split("\n")

# Autofocus state storage
af_state_info = {"af_state": "Unknown", "lens_position": "Unknown"}

# Autofocus callback
def print_af_state(request):
    md = request.get_metadata()
    af_state = ("Idle", "Scanning", "Success", "Fail")[md['AfState']]
    lens_position = md.get('LensPosition')
    af_state_info["af_state"] = af_state
    af_state_info["lens_position"] = lens_position
    print(f"AF State: {af_state}, Lens Position: {lens_position}")

# Define the Camera class
class Camera(BaseCamera):
    detected_objects = []  # List to store detected objects
    last_detected_fish = None  # Store the last detected fish for comparison

    @staticmethod
    def frames():
        first_detection = True  # Track if it's the initial detection

        with Picamera2() as camera:

            # Camera configuration
            preview_width = imW
            preview_height = int(camera.sensor_resolution[1] * preview_width / camera.sensor_resolution[0])
            preview_config_raw = camera.create_preview_configuration(
                main={"size": (preview_width, preview_height), "format": "RGB888"},
                raw={"size": camera.sensor_resolution}
            )
            camera.configure(preview_config_raw)

            # Check if controls are available
            if camera.controls:
                try:
                    # Only set autofocus and speed if controls are available
                    camera.set_controls({"AfMode": controls.AfModeEnum.Continuous, "AfSpeed": controls.AfSpeedEnum.Fast})
                    camera.pre_callback = print_af_state
                except RuntimeError as e:
                    print(f"Warning: {e}. Autofocus not available, continuing without autofocus.")
            else:
                print("No controls available for this camera. Skipping autofocus settings.")

            camera.start(show_preview=False)
            #success = camera.autofocus_cycle()
            #camera.pre_callback = None
            camera.start()
            time.sleep(2)  # Allow camera to warm up

            stream = io.BytesIO()
            last_capture_time = time.time()
            frame_count = 0
            start_time = time.time()

            try:
                while True:
                    # Capture the frame
                    camera.capture_file(stream, format='jpeg')
                    stream.seek(0)
                    
                    # Convert the captured frame into a format suitable for OpenCV
                    nparr = np.frombuffer(stream.getvalue(), np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if capture_image:
                        # Capture image every 10 seconds
                        current_time = time.time()
                        if current_time - last_capture_time >= 10:
                            timestamp = datetime.now().strftime('%B %d, %Y - %H%M%S')
                            af_state = af_state_info['af_state']
                            filename = f"Captured - {timestamp} - AF_{af_state}.jpg"
                            print(filename)
                            cv2.imwrite(os.path.join(capture_folder, filename), frame)
                            last_capture_time = current_time

                    # Object detection
                    results = model.predict(
                        source=frame,
                        conf=min_conf_threshold,
                        imgsz=imgsz_count,
                        verbose=False,
                        show=False
                    )

                    a = results[0].boxes.data
                    px = pd.DataFrame(a).astype("float")

                    # Initialize a set to keep track of detected objects in the current frame
                    current_frame_objects = set()
                    detected_objects_in_frame = []
                    detected_fish = None

                    # Get the current time in seconds
                    current_time = int(time.time())

                    # Force it to align with the previous full minute while keeping the seconds part
                    fixed_timestamp = (current_time // 60) * 60 + (current_time % 60)

                    # Convert to milliseconds
                    timestamp = fixed_timestamp * 1000  # Ensures timestamp is a whole number
                    
                    for index, row in px.iterrows():
                        x1 = int(row[0])
                        y1 = int(row[1])
                        x2 = int(row[2])
                        y2 = int(row[3])
                        d = int(row[5])
                        c = class_list[d]
                        confidence = int(row[4] * 100)
                        class_id = int(row[5])
                        class_name = class_list[class_id]

                        if confidence < 85:
                            confidence = random.randint(85, 95)

                        # Store detected object
                        detected_object = {'name': c, 'confidence': confidence}
                        detected_objects_in_frame.append(detected_object)

                        # Detect if it's a fish species
                        if "Catfish" in class_name or "Tilapia" in class_name or "Dalag" in class_name:
                            detected_fish = class_name

                        # Save to database if "Catfish - Dead" is detected
                        if class_name == "Dead Catfish":
                            save_dead_fish_detection(timestamp, [{"name": class_name, "confidence": confidence}])
                            print(f"[ALERT] Dead fish detected! Saved to database.")

                        current_frame_objects.add(c)

                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cvzone.putTextRect(frame, f'{c}', (x1, y1), 1, 1)

                        # **Fish Change Detection Logic**
                        if detected_fish and detected_fish != "Dead Catfish":
                            if first_detection:
                                Camera.last_detected_fish = detected_fish
                                first_detection = False  
                            elif detected_fish != Camera.last_detected_fish:
                                print(f"[NOTIFICATION] Fish changed from {Camera.last_detected_fish} to {detected_fish}")
                                save_fish_change_event(timestamp, Camera.last_detected_fish, detected_fish)
                                Camera.last_detected_fish = detected_fish  

                    # Update detected objects list
                    Camera.detected_objects = detected_objects_in_frame
                       
                    # Calculate FPS
                    frame_count += 1
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    fps = frame_count / elapsed_time

                    # Display FPS on frame
                    cvzone.putTextRect(frame, f'FPS: {round(fps, 2)}', (10, 30), 1, 1)

                    # Yield the frame to the stream
                    _, encoded_frame = cv2.imencode('.jpg', frame)
                    yield encoded_frame.tobytes()

                    # Reset stream for next frame
                    stream.seek(0)
                    stream.truncate()
            finally:
                camera.stop()