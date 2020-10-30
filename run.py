# file to run the program
from PoseEstimationImg import *
import cv2
import time 
import numpy as np
cap = cv2.VideoCapture(0)

pose = PoseEstimation()
pose.startUI()