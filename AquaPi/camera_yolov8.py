import io
import time
import cv2
import pandas as pd
import numpy as np
import cvzone
import argparse
import os

from picamera2 import Picamera2
from libcamera import controls

from base_camera import BaseCamera
from ultralytics import YOLO


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
args = parser.parse_args()

MODEL_NAME = args.modeldir
GRAPH_NAME = args.graph
LABELMAP_NAME = args.labels
imgsz_count = int(args.imgsz)
min_conf_threshold = float(args.threshold)
resW, resH = args.resolution.split('x')
imW, imH = int(resW), int(resH)

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

def print_af_state(request):
    md = request.get_metadata()
    print(("Idle", "Scanning", "Success", "Fail")[md['AfState']], md.get('LensPosition'))
    
# Define the Camera class
class Camera(BaseCamera):
    detected_objects = []  # List to store detected objects
    
    @staticmethod
    def frames():
        with Picamera2() as camera:
            camera.pre_callback = print_af_state
            preview_width = imW
            preview_height = int(camera.sensor_resolution[1] * preview_width / camera.sensor_resolution[0])
            preview_config_raw = camera.create_preview_configuration(
                main={"size": (preview_width, preview_height), "format": "RGB888"},
                raw={"size": camera.sensor_resolution}
            )
            camera.configure(preview_config_raw)
            camera.set_controls({"AfMode": controls.AfModeEnum.Continuous, "AfSpeed": controls.AfSpeedEnum.Fast})
            camera.start(show_preview=False)
            #success = camera.autofocus_cycle()
            #camera.pre_callback = None
            camera.start()
            time.sleep(2)  # Allow camera to warm up

            stream = io.BytesIO()
            frame_count = 0
            start_time = time.time()

            try:
                while True:
                    camera.capture_file(stream, format='jpeg')
                    stream.seek(0)
                    
                    # Convert the captured frame into a format suitable for OpenCV
                    nparr = np.frombuffer(stream.getvalue(), np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

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

                    # Loop over all detections and store detected objects
                    detected_objects_in_frame = []
                    for index, row in px.iterrows():
                        x1 = int(row[0])
                        y1 = int(row[1])
                        x2 = int(row[2])
                        y2 = int(row[3])
                        d = int(row[5])
                        c = class_list[d]

                        # Store detected object
                        detected_object = {'name': c, 'confidence': int(row[4] * 100)}
                        detected_objects_in_frame.append(detected_object)
                        current_frame_objects.add(c)

                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cvzone.putTextRect(frame, f'{c}', (x1, y1), 1, 1)

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
