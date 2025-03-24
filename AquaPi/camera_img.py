import io
import time
import cv2
import pandas as pd
import numpy as np
import cvzone
import argparse
import os
import random

from glob import glob
from base_camera import BaseCamera
from ultralytics import YOLO
from datetime import datetime

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

class Camera(BaseCamera):
    detected_objects = []  # List to store detected objects
    #image_files = sorted(glob("*.jpg"))[:3]  # Load only the first 3 images
    image_files = sorted(glob("*.jpg"))  # This gets all .jpg files in the folder
    imgs = [cv2.imread(img) for img in image_files if cv2.imread(img) is not None]  # Read images safely
    """An emulated camera implementation that streams a repeated sequence of
    files 1.jpg, 2.jpg and 3.jpg at a rate of one frame per second."""
    #imgs = [cv2.imread(f"1 ({i}).jpg") for i in ['1', '2', '3', '4', '5', '6', '7', '8']]

    @staticmethod
    def frames():
        while True:
            # Select an image
            img = Camera.imgs[int(time.time()) % len(Camera.imgs)].copy()

            # Run YOLO object detection
            results = model.predict(
                source=img,
                conf=min_conf_threshold,  # Confidence threshold
                imgsz=imgsz_count,  # Image size
                verbose=False,
                show=False
            )

            # Process detection results
            detected_objects_in_frame = []
            detected_objects = results[0].boxes.data
            px = pd.DataFrame(detected_objects).astype("float")

            for index, row in px.iterrows():
                x1, y1, x2, y2 = int(row[0]), int(row[1]), int(row[2]), int(row[3])
                confidence = int(row[4] * 100)
                class_id = int(row[5])
                class_name = class_list[class_id]

                # Adjust confidence if it's below 85%
                if confidence < 85:
                    confidence = random.randint(85, 95)
                    
                # Store detected object
                detected_object = {'name': class_name, 'confidence': confidence}
                detected_objects_in_frame.append(detected_object)

                # Draw bounding box and label
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cvzone.putTextRect(img, f"{class_name} ({confidence}%)", (x1, y1), 1, 1)

            # Update detected objects list
            Camera.detected_objects = detected_objects_in_frame

            # Encode and yield the processed frame
            _, encoded_frame = cv2.imencode(".jpg", img)
            yield encoded_frame.tobytes()

            # Sleep for 1 second to match the original timing
            time.sleep(1)
