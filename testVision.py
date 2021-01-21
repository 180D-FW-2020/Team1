from PoseEstimation import *
from ContourDetection import *
import cv2
import time
import numpy as np

timestart = time.perf_counter()
pose = PoseEstimation("MPI", "gpu")
detect = ContourDetection()

_, frame = cv2.VideoCapture(0).read()

_, points = pose.getPoints(frame)
# pose.getContourFromPoints(points, True)

print(time.perf_counter()-timestart)