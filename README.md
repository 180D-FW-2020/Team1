# Team1's Project for ECE180DA + DB
Chester Hulse, Erica Xie, Shalin Shah, Wesley Sakutori

We are implementing a virtual version of [Hole in the Wall](https://www.youtube.com/watch?v=sHpKiX87X2c) with added twists, including gesture and voice recognitiion for powerups, a virtual wall, and a multiplayer mode to play with friends.

# Dependencies 
See requirements.txt

# Installation for Users 
```
pip install pipreqs
pip install -r requirements.txt
```

# Running the Game
On your laptop:
```
python game.py
```
On the Raspberry Pi:
```
python mqtt.py
```

# Source Code Descriptions:
| File | Description |
| --- | --- |
| `GestureRecognition` | Contains gesture recognition code, including IMU libraries and gesture data.<br> - **Sources:** in-class labs<br> - **Decisions:** reeeeeeeeeee <br> - **Bugs:** reeeeeeeeee <br> - **TODO:** reeeeeeeeee|
| `graphics` | Includes images necesary for gameplay and user interface. |
| `pose` | Folder containing modules used by openpose for pose recognition. |
| `ContourDetection.py` | Contour detection code to check if someone is within the "hole". |
| `game.py` | Main code running the overall game. |
| `mqtt.py` | Code sending MQTT packets and running gesture recognition on the RPI. |
| `PoseEstimation.py` | Code using the OpenPose library to recognize a player's position on the screen. |
| `README.md` | This file with usage and documentation. |
| `requirements.txt` | Dependency information. |
| `setup.py` | Script to set up the game. |
| `voice.py` | Voice recognition code to activate powerups. |