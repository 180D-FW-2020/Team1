from PoseEstimation import *
from ContourDetection import *
import cv2
import time
import numpy as np

timestart = time.perf_counter()
pose = PoseEstimation("COCO")
detect = ContourDetection()

_, frame = cv2.VideoCapture(0).read()

pose.getPoints(frame)

print(time.perf_counter()-timestart)