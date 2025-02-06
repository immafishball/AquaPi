import os
import cv2
import io

import argparse
import numpy as np
import sys
import time
import importlib.util

from picamera2 import Picamera2
from base_camera import BaseCamera
from libcamera import controls

from threading import Thread
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
parser.add_argument('--resolution', help='Desired webcam resolution in WxH. If the webcam does not support the resolution entered, errors may occur.',
                    default='1280x720')
parser.add_argument('--edgetpu', help='Use Coral Edge TPU Accelerator to speed up detection',
                    action='store_true')
parser.add_argument('--capture', help='Enable image capture every 10 seconds',
                    action='store_true')

args = parser.parse_args()

MODEL_NAME = args.modeldir
GRAPH_NAME = args.graph
LABELMAP_NAME = args.labels
min_conf_threshold = float(args.threshold)
resW, resH = args.resolution.split('x')
imW, imH = int(resW), int(resH)
use_TPU = args.edgetpu
capture_image = args.capture

# Create Capture folder if it doesn't exist
capture_folder = os.path.join(os.getcwd(), 'Capture')
os.makedirs(capture_folder, exist_ok=True)

# Import TensorFlow libraries
# If tflite_runtime is installed, import interpreter from tflite_runtime, else import from regular tensorflow
# If using Coral Edge TPU, import the load_delegate library
pkg = importlib.util.find_spec('tflite_runtime')
if pkg:
    from tflite_runtime.interpreter import Interpreter
    if use_TPU:
        from tflite_runtime.interpreter import load_delegate
else:
    from tensorflow.lite.python.interpreter import Interpreter
    if use_TPU:
        from tensorflow.lite.python.interpreter import load_delegate

# If using Edge TPU, assign filename for Edge TPU model
if use_TPU:
    # If user has specified the name of the .tflite file, use that name, otherwise use default 'edgetpu.tflite'
    if (GRAPH_NAME == 'detect.tflite'):
        GRAPH_NAME = 'edgetpu.tflite'       

# Get path to current working directory
CWD_PATH = os.getcwd()

# Path to .tflite file, which contains the model that is used for object detection
PATH_TO_CKPT = os.path.join(CWD_PATH,MODEL_NAME,GRAPH_NAME)

# Path to label map file
PATH_TO_LABELS = os.path.join(CWD_PATH,MODEL_NAME,LABELMAP_NAME)

# Load the label map
with open(PATH_TO_LABELS, 'r') as f:
    labels = [line.strip() for line in f.readlines()]

# Have to do a weird fix for label map if using the COCO "starter model" from
# https://www.tensorflow.org/lite/models/object_detection/overview
# First label is '???', which has to be removed.
if labels[0] == '???':
    del(labels[0])

# Load the Tensorflow Lite model.
# If using Edge TPU, use special load_delegate argument
if use_TPU:
    interpreter = Interpreter(model_path=PATH_TO_CKPT,
                              experimental_delegates=[load_delegate('libedgetpu.so.1.0')])
    print(PATH_TO_CKPT)
else:
    interpreter = Interpreter(model_path=PATH_TO_CKPT)

interpreter.allocate_tensors()

# Get model details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
height = input_details[0]['shape'][1]
width = input_details[0]['shape'][2]

floating_model = (input_details[0]['dtype'] == np.float32)

input_mean = 127.5
input_std = 127.5

# Check output layer name to determine if this model was created with TF2 or TF1,
# because outputs are ordered differently for TF2 and TF1 models
outname = output_details[0]['name']

if ('StatefulPartitionedCall' in outname): # This is a TF2 model
    boxes_idx, classes_idx, scores_idx = 1, 3, 0
else: # This is a TF1 model
    boxes_idx, classes_idx, scores_idx = 0, 1, 2

freq = cv2.getTickFrequency()

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
    
    @staticmethod
    def frames():
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

            try:
                while True:
                    camera.capture_file(stream, format='jpeg')
                    stream.seek(0)

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

                    # Start timer (for calculating frame rate)
                    t1 = cv2.getTickCount()

                    # Convert the captured frame to the format required by the model
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_resized = cv2.resize(frame_rgb, (width, height))
                    input_data = np.expand_dims(frame_resized, axis=0)

                    if floating_model:
                        input_data = (np.float32(input_data) - input_mean) / input_std

                    interpreter.set_tensor(input_details[0]['index'], input_data)
                    interpreter.invoke()

                    # Retrieve detection results
                    boxes = interpreter.get_tensor(output_details[boxes_idx]['index'])[0] # Bounding box coordinates of detected objects
                    classes = interpreter.get_tensor(output_details[classes_idx]['index'])[0] # Class index of detected objects
                    scores = interpreter.get_tensor(output_details[scores_idx]['index'])[0] # Confidence of detected objects
                    
                    # Initialize a set to keep track of detected objects in the current frame
                    current_frame_objects = set()

                    for i in range(len(scores)):
                        if ((scores[i] > min_conf_threshold) and (scores[i] <= 1.0)):
                            ymin = int(max(1, (boxes[i][0] * imH)))
                            xmin = int(max(1, (boxes[i][1] * imW)))
                            ymax = int(min(imH, (boxes[i][2] * imH)))
                            xmax = int(min(imW, (boxes[i][3] * imW)))

                            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (10, 255, 0), 2)
                            object_name = labels[int(classes[i])]
                            label = '%s: %d%%' % (object_name, int(scores[i] * 100))
                            labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                            label_ymin = max(ymin, labelSize[1] + 10)
                            cv2.rectangle(frame, (xmin, label_ymin - labelSize[1] - 10), (xmin + labelSize[0], label_ymin + baseLine - 10), (255, 255, 255), cv2.FILLED)
                            cv2.putText(frame, label, (xmin, label_ymin - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

                            # Store detected objects
                            detected_object = {'name': object_name, 'confidence': int(scores[i] * 100)}
                            current_frame_objects.add(object_name)
                            
                            # Add the detected object to the list if it's not already present
                            if detected_object not in Camera.detected_objects:
                                Camera.detected_objects.append(detected_object)

                    # Remove objects that were detected in previous frames but not in the current frame
                    Camera.detected_objects = [obj for obj in Camera.detected_objects if obj['name'] in current_frame_objects]

                    # Calculate framerate
                    t2 = cv2.getTickCount()
                    time1 = (t2-t1)/freq
                    frame_rate_calc= 1/time1

                    # Draw framerate in corner of frame
                    cv2.putText(frame,'FPS: {0:.2f}'.format(frame_rate_calc),(30,50),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,0),2,cv2.LINE_AA)
                    
                    # Yield the frame to the stream
                    _, encoded_frame = cv2.imencode('.jpg', frame)
                    yield encoded_frame.tobytes()

                    stream.seek(0)
                    stream.truncate()

            finally:
                camera.stop()