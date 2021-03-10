# Team1's Project for ECE180DA + DB
Chester Hulse, Erica Xie, Shalin Shah, Wesley Sakutori

We are implementing a virtual version of [Hole in the Wall](https://www.youtube.com/watch?v=sHpKiX87X2c) with added twists, including gesture and voice recognitiion for powerups, a virtual wall, and a multiplayer mode to play with friends.

# Dependencies 
See requirements.txt

# Installation for Users
Make sure to have [anaconda](https://docs.anaconda.com/anaconda/install/) or [miniconda](https://docs.conda.io/en/latest/miniconda.html) installed before running the setup script. 
Clone our [repo](https://github.com/180D-FW-2020/Team1). 
Download and change [key.py](https://drive.google.com/file/d/1E3bpf4huUrUgIFHYl_1z13nRmQvIFrkn/view?usp=sharing) to your passwords + Raspberry Pi login information. Put in the main directory. 

If you're on a PC:  
 
```
./setup_win.sh
conda activate hitw
pip install pipwin 
pipwin install pyaudio
```
If you're on a MAC: 
```
chmod +x setup.sh 
./setup_mac.sh
conda activate hitw
pip install pyaudio
```
On the Raspberry Pi (optional):
```
cd GestureRecognition 
chmod +x setup.sh
./setup.sh
```

# Running the Game
On your laptop:
```
conda activate hitw
python game.py
```

# User Manual 
Read our [User Manual](https://docs.google.com/document/d/1mSSGqndTtNvM9dn26AQYYy9mmHIH6x1cDG8x9IvnCus/edit?usp=sharing) for more details on how to play the game and some tips for troubleshooting! 

# Source Code Descriptions:
| File | Description |
| --- | --- |
| `GestureRecognition` | Contains gesture recognition code, including IMU libraries and gesture data.<br> **More Details inside the folder**
| `graphics` | Includes images necesary for gameplay and user interface.<br> - **Sources:** In-class OpenCV labs<br> - **Decisions:** Use OpenCV for graphics for now, might migrate to pygame in the future <br> - **Bugs:** None <br> - **TODO:** Transition to pygame|
| `pose` | Folder containing modules used by our OpenCV DNN model for pose recognition.<br>**More Details inside the folder**
| `ContourDetection.py` | Contour detection code to check if someone is within the "hole".<br> - **Sources:** OpenCV, OpenPose output points<br> - **Decisions:** All joint points are equally weighted for this decision  <br> - **Bugs:** None<br> - **TODO:** None|
| `game.py` | Main code running the overall game.<br> - **Sources:** All sub-module files and in-class labs<br> - **Decisions:** Singleplayer and Multiplayer implemented, try and run everything in the background and organize events into callbacks. Send MQTT packets and runs gesture recognition on the RPI. <br> - **Bugs:** A player leaving a game sometimes freezes the program. <br> - **TODO:** Move to pygame for music and a better UI.|
| `PoseEstimation.py` | Code using the OpenPose library to recognize a player's position on the screen.<br> - **Sources:** OpenPose models and datasets<br> - **Decisions:** prioritize pose detection speed with model choice <br> - **Bugs:** None<br> - **TODO:** GPU (NVIDIA CUDA) support, improve speed|
| `README.md` | This file with usage and documentation. |
| `requirements.txt` | Dependency information. |
| `setup.py` | Script to set up the game. |
| `voice.py` | Voice recognition code to activate powerups.<br> - **Sources:** In-class labs<br> - **Decisions:** Use microphone built into laptop. Use google voice with no limit on phrase length. <br> - **Bugs:** Slow and sometimes hangs the program when closing. <br> - **TODO:** Using Google Voice for now but may upgrade to more consistent recognizer in the future.|
