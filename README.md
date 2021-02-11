# Team1's Project for ECE180DA + DB
Chester Hulse, Erica Xie, Shalin Shah, Wesley Sakutori

We are implementing a virtual version of [Hole in the Wall](https://www.youtube.com/watch?v=sHpKiX87X2c) with added twists, including gesture and voice recognitiion for powerups, a virtual wall, and a multiplayer mode to play with friends.

# Dependencies 
See requirements.txt

# Installation for Users
Clone our [repo](https://github.com/180D-FW-2020/Team1). 
Download our trained dnn model [pose_iter_160000.caffemodel](https://drive.google.com/file/d/1opfbTlgxeEw4yokoNndD36NVYGc8c0Xe/view?usp=sharing). 
 
```
./setup.sh
conda activate hitw
pip install pipwin 
pipwin install pyaudio
```

# Running the Game
On your laptop:
```
conda activate hitw
python game.py
```
On the Raspberry Pi:
```
cd GestureRecognition 
./setup.sh
conda activate hitw
python mqtt.py #single player 
python mqtt.py -r *insert 6 character room code* -u *insert nickname* #multiplayer
```

# User Manual 
Read our [User Manual](https://docs.google.com/document/d/1mSSGqndTtNvM9dn26AQYYy9mmHIH6x1cDG8x9IvnCus/edit?usp=sharing) for more details on how to play the game! 

# Source Code Descriptions:
| File | Description |
| --- | --- |
| `GestureRecognition` | Contains gesture recognition code, including IMU libraries and gesture data.<br> **More Details inside the folder**
| `graphics` | Includes images necesary for gameplay and user interface.<br> - **Sources:** in-class OpenCV labs<br> - **Decisions:** Use OpenCV for graphics for now, might migrate to Unity in the future. <br> - **Bugs:** Originally had x/y coordinates backwards for pixels, fixed now. <br> - **TODO:** transition to unity|
| `pose` | Folder containing modules used by OpenPose for pose recognition.<br>**More Details inside the folder**
| `ContourDetection.py` | Contour detection code to check if someone is within the "hole".<br> - **Sources:** openCV, OpenPose output points<br> - **Decisions:** All joint points are equally weighted for this decision.  <br> - **Bugs:** None<br> - **TODO:** Convert to work with contours sent over the network|
| `game.py` | Main code running the overall game.<br> - **Sources:** All sub-module files<br> - **Decisions:** Singleplayer for now, try and run everything in the background and organize events into callbacks. <br> - **Bugs:** none that we know of <br> - **TODO:** Make better contour creation tool for network poses|
| `mqtt.py` | Code sending MQTT packets and running gesture recognition on the RPI.<br> - **Sources:** in-class labs, JSON library<br> - **Decisions:** Use JSON to encode dictionaries into strings <br> - **Bugs:** none <br> - **TODO:** flush out more MQTT functionality when this becomes multiplayer.|
| `PoseEstimation.py` | Code using the OpenPose library to recognize a player's position on the screen.<br> - **Sources:** OpenPose models and datasets<br> - **Decisions:** prioritize pose detection speed with model choice <br> - **Bugs:** None<br> - **TODO:** Dynamic contour creation, camera spec calibration, GPU (NVIDIA CUDA) support, improve speed|
| `README.md` | This file with usage and documentation. |
| `requirements.txt` | Dependency information. |
| `setup.py` | Script to set up the game. |
| `voice.py` | Voice recognition code to activate powerups.<br> - **Sources:** in-class labs<br> - **Decisions:** Use microphone built into laptop. Use google voice for now but may upgrade to more consistent recognizer in the future. <br> - **Bugs:** Sometimes words aren't recognized, could be improved with better recognizer. <br> - **TODO:** Send voice commands over mqtt as well for multiplayer.|