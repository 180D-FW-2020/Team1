# Gesture Recognition
This is the gesture recognition code that runs on the Raspberry Pi. There is no need to actually call any of these functions when playing the game because the game automatically connects remotely to the Raspberry Pi. 

If you would like to see the data collected and the machine learning Jupyter Notebook, you can view it [here](https://drive.google.com/drive/folders/18kIA0xddDaSEXMj3cG63gM1fOaFI8LR3?usp=sharing). 

# Installation for Users 
```
cd GestureRecognition 
chmod +x setup.sh
./setup.sh
```

# Running the Game
```
source activate hitw
python mqtt.py #single player 
python mqtt.py -r 'insert 6 character room code' -n 'insert nickname' #multiplayer
```

# Source Code Descriptions
| File | Description |
| --- | --- |
| `models` | Models generated with machine learning Jupyter Notebook. |
| `collect_data.py` | Reads the angles from the accelerometer, gyroscope and magnetometer on a BerryIMU connected to a Raspberry Pi for an customizable duration into a specfied file. The collection is activated when a certain acceleration threshold is passed. Also includes two filters (low pass and median) to improve the values returned from BerryIMU by reducing noise. |
| `gesture_detector.py` | Reads angles from the accelerometer, gyroscope and magnetometer and runs the gesture recognition code using the model in /models. The collection is activated when a certain acceleration threshold is passed. |
| `mqtt.py` | Connects to the client and runs the gesture classification code. Sends the results of the classification to the broker. |
| `calibrateBerryIMU.py` | Calibration code from BerryIMU. |
| `README.md` | This file with usage and documentation. |
| `requirements.txt` | Dependency information. |
| `setup.sh` | Setup script to install all dependencies. |

# Sources
- Collecting data using [OzzMaker BerryIMUv3 (LSM6DSL and LIS3MDL)](http://ozzmaker.com/berryimu) 
- Machine Learning Training based off of [Magic Wand Project by Jennifer Wang](https://github.com/jewang/gesture-demo)

# Dependencies 
See requirements.txt

# TODO
- Refine current model by generating more samples from different people. 
- Speed up the loading of the machine learning model. 
