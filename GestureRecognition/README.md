# Source Code Descriptions:
| File | Description |
| --- | --- |
| `models` | Models generated with machine learning. |
| `collect_data.py` | Reads the angles from the accelerometer, gyroscope and magnetometer on a BerryIMU connected to a Raspberry Pi for an customizable duration into a specfied file. Also includes two filters (low pass and median) to improve the values returned from BerryIMU by reducing noise. |
| `gesture_detector.py` | Reads angles from the accelerometer, gyroscope and magnetometer and runs the gesture recognition code using the model in /models. |
| `mqtt.py` | Connects to the client and runs the gesture classification code. |
| `calibrateBerryIMU.py` | Calibration code from BerryIMU. |
| `README.md` | This file with usage and documentation. |
| `requirements.txt` | Dependency information. |
| `utils.py` | Utility functions used by both collect_data.py and gesture_detector.py to collect data. |

# Source Code

Collecting data using [OzzMaker BerryIMUv3 (LSM6DSL and LIS3MDL)](http://ozzmaker.com/berryimu) 

---------------------------------------------------------------------

Machine Learning Training based off of [Magic Wand Project by Jennifer Wang](https://github.com/jewang/gesture-demo)

# Dependencies 
See requirements.txt

# Installation for Users 
```
pip install pipreqs
pip install -r requirements.txt
```

