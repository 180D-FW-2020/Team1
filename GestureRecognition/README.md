# Source Code Descriptions:
| File | Description |
| --- | --- |
| `models` | Models generated with machine learning. |
| `collect_data.py` | Reads the angles from the acceleromter, gyrscope and mangnetometer on a BerryIMU connected to a Raspberry Pi for an customizable duration into a specfied file. Also includes two filters (low pass and median) to improve the values returned from BerryIMU by reducing noise. |
| `gesture_detector.py` | Folder containing modules used by openpose for pose recognition. |
| `mqtt.py` | Connects to the client and runs the gesture classification code. |
| `calibrateBerryIMU.py` | Calibration code from BerryIMU. |
| `README.md` | This file with usage and documentation. |
| `requirements.txt` | Dependency information. |
| `utils.py` | Utility functions used by both collect_data.py and gesture_detector.py to collect data. |

# Source Code

[OzzMaker Berry IMU](http://ozzmaker.com/berryimu)

BerryIMUv1 uses LSM9DS0 IMU
BerryIMUv2 uses LSM9DS1 IMU
BerryIMUv3 uses LSM6DSL and LIS3MDL

---------------------------------------------------------------------

Machine Learning Training based off of [Magic Wand Project by Jennifer Wang](https://github.com/jewang/gesture-demo)

# Dependencies 
See requirements.txt

# Installation for Users 
```
pip install pipreqs
pip install -r requirements.txt
```

