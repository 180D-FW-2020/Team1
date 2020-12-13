from PoseEstimation import *
from ContourDetection import *
import cv2
import time 
import numpy as np

pose = PoseEstimation()
contour = ContourDetection()
cap = cv2.VideoCapture(0)
_, frame = cap.read()
frame, points = pose.getPoints(frame, True, True)
print(contour.isWithinContour(points, cv2.imread('graphics\poses\easy\left.jpg')))