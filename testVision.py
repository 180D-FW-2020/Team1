from PoseEstimation import *
from ContourDetection import *
import cv2
import time
import numpy as np

#timestart = time.perf_counter()
pose = PoseEstimation("cpu")
detect = ContourDetection()
overlay = cv2.imread('graphics\test.png')

while(True):
    _, frame = cv2.VideoCapture(0).read()
    _, points = pose.getPoints(frame)
    frame[0:480, 0:640] = overlay
    cv2.imshow("overlay", overlay)

    nPoints = detect.isWithinContour(points,'\graphics\test.png')
    cv2.line(frame, (0,0),(0,nPoints*40))
    if (nPoints == 15):
        break

# pose.getContourFromPoints(points, True)

#print(time.perf_counter()-timestart) 