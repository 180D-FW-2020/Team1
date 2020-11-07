from PoseEstimation import *
from ContourDetection import *
import cv2
import time
import numpy as np

pose = PoseEstimation()
detect = ContourDetection()

frame = pose.getFrame()
#pose.getContour(frame, True)
_, points = pose.getPoints(frame, True)

print(detect.isWithinContour(points, 'Output-Contour.jpg'))