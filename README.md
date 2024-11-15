# 🌟 AquaPi

Monitor your Aquarium's Temperature and Water Level. With DFRobot Circuit Boards and Probe upgrades, you can also monitor your pH, Dissolved Oxygen, Temperature, Turbidity and other DFRobot circuits and probes. It can also identify types of fish to set conditions of the environment to the selected type of fish.
Powered by an Raspberry Pi and Controlled by IoT. You can set alerts for anything, make automations for auto-top-off, and see beautiful graphs of your aquarium's data (see screenshot).

## Appearance

This app simply made during my college as a final output for Project and Design 2. The UI is fully responsive therefore viewing it on small screens should be fine.

## 🎯 Features

- Monitoring System [Local and Online]
- Feeding System [Schedule and Manual]
- AI System [Fish Identification]
- Water Parameter Sensors
- Database [SQLite]

## Getting Started

### 🔑 Dependencies

The project dependencies include Raspberry Pi OS (64-bit) - Bookworm, which serves as the operating system. Development tools such as Visual Studio Code, Python (3.9), and TensorFlow are essential for coding, testing, and deploying the application. Additionally, XRDP and WinSCP are utilized for remote desktop access and secure file transfer between systems.

<details><summary><b>Show Requirements</b></summary>

- Raspberry Pi OS (64-bit) - Bookworm or Bullseye
- Visual Studio Code
- Python (3.2 ~ 3.9.12)
- YOLOv8
- TensorFlow
- XRDP
- WinSCP

</details>

### ⚙️ Installation

This guide provides step-by-step instructions for how to set up YOLOv8 on the Raspberry Pi and use it to run object detection models. It also shows how to set up the Coral USB Accelerator on the Pi and run Edge TPU detection models. It works for the Raspberry Pi 3 and Raspberry Pi 4 running Rasbpian Bullseye or Bookworm.

<details><summary><b>Show Instructions</b></summary>

### 1. Install Raspberry Pi OS (64-bit)

To get started, install Raspberry Pi OS (64-bit) on your microSD card. The recommended method is using the [Raspberry Pi Imager](https://downloads.raspberrypi.org/imager/imager_latest.exe), which provides a quick and straightforward way to set up Raspberry Pi OS and other operating systems. For better compatibility, use either [Raspberry Pi OS with desktop - Bookworm](https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2024-10-28/2024-10-22-raspios-bookworm-arm64.img.xz) or [Raspberry Pi OS with desktop - Bullseye](https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2024-07-04/2024-07-04-raspios-bookworm-arm64.img.xz).

### 2. Install Remote Desktop Connection (XRDP) Optional

To install XRDP on your Raspberry Pi, run the following commands in the terminal:

    sudo apt update && sudo apt upgrade
    sudo apt install xrdp
 
Additional configuration is required as Bookworm doesn't allow the default user "pi" to connect and also makes XRDP run slow.

<details><summary><b>Steps to allow the default user "pi" to log in with XRDP:</b></summary>

#### 1. Open the XRDP configuration file:
    sudo nano /etc/X11/xrdp/xorg.conf

#### 2. Find the line:
    Option "DRMDevice" "/dev/dri/renderD128"

#### 3. Change it to:
    #Option "DRMDevice" "/dev/dri/renderD128"
    Option "DRMDevice" ""
    
</details>

<details><summary><b>Bullseye OS causes XRDP to lag</b></summary>

#### 1. Open the XRDP configuration file:
    sudo nano /usr/bin/startlxde-pi

#### 2. Find the line:
    $TOTAL_MEM -ge 2048

#### 3. Change it to:
    $TOTAL_MEM -ge 20480

</details>

#### Save and exit: **Ctrl + X**, **Ctrl + Y**, and **Enter**.

#### Run this command to find your Raspberry Pi IP
    hostname -I

### 3.Clone this Repository
    git clone https://github.com/immafishball/AquaPi.git

### 4. Installing required dependencies

Next, we'll install YOLOv8, OpenCV, and all the dependencies needed for both packages. OpenCV is needed to run YOLOv8, the scripts in this repository use it to grab images and draw detection results on them.

To make things easier, I wrote a shell script that will automatically download and install all the packages and dependencies. Run it by issuing:

<details><summary><b>Python 3.9.12 - Only for Bookworm</b></summary>

#### 1. Go to Projects Directory:
    mv AquaPi Projects
    cd Projects
    python -m venv --system-site-packages env

#### 2. Download and Run the Pyenv Installer:
    curl https://pyenv.run | bash

#### 3. Update Shell Configuration:
    echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
    echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
    echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
    exec "$SHELL"

#### 4. Install Dependencies:
    sudo apt-get install --yes libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libgdbm-dev lzma lzma-dev tcl-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev wget curl make build-essential openssl

#### 5. Install Python 3.9.12:
    pyenv install 3.9.12

#### 6. Set Python 3.9.12 as Local Version:
    pyenv local 3.9.12

#### 7. Verify Python Installation:
    python --version

#### 8. Reboot your Raspberry Pi:
    sudo reboot now

</details>

------------------------

<details><summary><b>EdgeTPU & YOLOv8</b></summary>

#### 1. Create and Activate the Virtual Environment:
    mv AquaPi Projects
    cd Projects
    python -m venv --system-site-packages env
    source env/bin/activate

#### 2. Install PyTorch Libraries:
    pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2

#### 3. Install Edge TPU Silva:
    pip install edge-tpu-silva

#### 4. Run Silva TPU Linux Setup:
    silvatpu-linux-setup

#### 4. Reboot your Raspberry Pi:
    sudo reboot now

</details>

------------------------

<details><summary><b>Project Dependencies</b></summary>

#### 1. Go back to the virtual environment:
    cd Projects
    source env/bin/activate

#### 2. Dependencies for AquaPi:
The --break-system-packages flag in pip allows to override the externally-managed-environment error and install Python packages system-wide.

**Note: Usage of this flag shouldn't be abused.**

    pip install RPi.GPIO flask flask_cors smbus cvzone apscheduler numpy==1.24.4
    sudo apt-get install --yes sqlite3 sqlitebrowser

#### 3. Set Crontab for Fish Feeder:
Well have to set a cron job scheduler for our fish feeder checking for every minute if there is exisiting timed set in our database.

    crontab -e

Select an editor (if prompted):
If this is your first time setting up a crontab, you might be prompted to choose an editor. The default is usually nano, which is simple to use.

Add the cron job:
Once the editor opens, add the following line to run your script every minute:

    * * * * * /usr/bin/python3 /home/pi/Projects/AquaPi/cron_script.py

Verify the cron job:
You can confirm that the cron job has been added by running:

    crontab -l

</details>

</details>

### 👀 Usage
This project uses object detection models to identify objects in real-time from a webcam feed. The project supports both YOLOv8 and TensorFlow Lite models. Below are instructions on how to run the code for each model type.

#### Activate the Virtual Environment:
    cd Projects
    source env/bin/activate
    cd AquaPi

<details><summary><b>YOLOv8 Instructions</b></summary>

#### To run the object detection using a YOLOv8 model, use the following command:
    CAMERA=yolov8 python3 app.py --modeldir=<MODEL_DIRECTORY> --graph=<MODEL_FILE>.tflite --labels=<LABELMAP_FILE> --threshold=<CONFIDENCE_THRESHOLD> --resolution=<WEBCAM_RESOLUTION> --imgsz=<IMAGE_SIZE>

#### Arguments
- --modeldir: Folder where the .tflite file is located (e.g., Model).
- --graph: Name of the .tflite file (e.g., 240_yolov8n_full_integer_quant_edgetpu.tflite).
- --labels: Name of the labelmap file (e.g., coco.txt).
- --threshold: Minimum confidence threshold for displaying detected objects (default: 0.5).
- --resolution: Desired webcam resolution in WxH (e.g., 640x360). Ensure your webcam supports this resolution.
- --imgsz: Image size for inference, can be a single integer or a tuple (default: 256).

#### Example Command:
    CAMERA=yolov8 python3 app.py --modeldir=Model --graph=240_yolov8n_full_integer_quant_edgetpu.tflite --labels=coco.txt --threshold=0.5 --resolution=640x360 --imgsz=256

</details>

<details><summary><b>TensorFlow Lite Instructions</b></summary>

#### To run the object detection using a TensorFlow Lite model, use the following command:
    CAMERA=tensorflow python3 app.py --modeldir=<MODEL_DIRECTORY> --graph=<MODEL_FILE>.tflite --labels=<LABELMAP_FILE> --threshold=<CONFIDENCE_THRESHOLD> --resolution=<WEBCAM_RESOLUTION> --edgetpu

#### Arguments
- --modeldir: Folder where the .tflite file is located (e.g., Sample_TFLite_model).
- --graph: Name of the .tflite file (e.g., detect.tflite).
- --labels: Name of the labelmap file (e.g., labelmap.txt).
- --threshold: Minimum confidence threshold for displaying detected objects (default: 0.5).
- --resolution: Desired webcam resolution in WxH (e.g., 1920x1080). Ensure your webcam supports this resolution.
- --edgetpu: Use Coral Edge TPU Accelerator to speed up detection (add this flag to enable).

#### Example Command:
    CAMERA=tensorflow python3 app.py --modeldir=Sample_TFLite_model --graph=detect.tflite --labels=labelmap.txt --threshold=0.5 --resolution=640x360

</details>

## 🧭 Roadmap
* [ ] Add Instructions for Custom Model
* [ ] Accesibility for sensors

## ‼️ Notice

This project can be run fully locally without any internet connection, otherwise you will need to have a connection to control the IoT devices.

