######## Simple Picture Taking Script #########
#
# This program takes pictures (in .jpg format) from a connected webcam and saves
# them in the specified directory. The default directory is 'Captured' and the
# default resolution is 1280x720.
#
# Example usage to save images in a directory named Sparrow at 1920x1080 resolution:
# python3 PictureTaker.py --imgdir=Sparrow --resolution=1920x1080

import cv2
import os
import argparse
import sys
import time

from datetime import datetime
from picamera2 import Picamera2
from libcamera import controls

# Define and parse input arguments
parser = argparse.ArgumentParser()
parser.add_argument('--imgdir', help='Folder to save images in (will be created if it doesn\'t exist already)',
                    default='Captured')
parser.add_argument('--resolution', help='Desired camera resolution in WxH.',
                    default='640x360')

args = parser.parse_args()
dirname = args.imgdir
if not 'x' in args.resolution:
    print('Please specify resolution as WxH. (example: 1920x1080)')
    sys.exit()
imW = int(args.resolution.split('x')[0])
imH = int(args.resolution.split('x')[1])

# Create output directory if it doesn't already exist
cwd = os.getcwd()
dirpath = os.path.join(cwd, dirname)
if not os.path.exists(dirpath):
    os.makedirs(dirpath)

def print_af_state(request):
    md = request.get_metadata()
    print(("Idle", "Scanning", "Success", "Fail")[md['AfState']], md.get('LensPosition'))
    
# Create an instance of the PiCamera2 object
cam = Picamera2()
cam.pre_callback = print_af_state
# Set the resolution of the camera preview
preview_width = imW
preview_height = int(cam.sensor_resolution[1] * preview_width / cam.sensor_resolution[0])
preview_config_raw = cam.create_preview_configuration(
    main={"size": (preview_width, preview_height), "format": "RGB888"},
    raw={"size": cam.sensor_resolution}
)
cam.configure(preview_config_raw)
cam.start(show_preview=False)
cam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
#success = cam.autofocus_cycle()
#cam.pre_callback = None
cam.start()
time.sleep(2)  # Allow camera to warm up

# Initialize display window
winname = 'Camera View (Press "q" to quit)'
cv2.namedWindow(winname)
cv2.moveWindow(winname, 50, 30)

print('Capturing images every 10 seconds. Press "q" to quit.')

# Record the time of the last image capture
last_capture_time = time.time()

try:
    while True:
        # Capture frame from the camera
        frame = cam.capture_array()

        # Display the camera feed
        cv2.imshow(winname, frame)

        # Check if 10 seconds have passed since the last capture
        if time.time() - last_capture_time >= 10:
            # Generate the filename using the current date and time
            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'captured_{current_time}.jpg'
            savepath = os.path.join(dirpath, filename)

            # Save the captured image
            cv2.imwrite(savepath, frame)
            print(f'Picture taken and saved as {filename}')

            # Update the last capture time
            last_capture_time = time.time()

        # Check if the user pressed the 'q' key to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print('Picture taking stopped by user.')

# Clean up
cv2.destroyAllWindows()
