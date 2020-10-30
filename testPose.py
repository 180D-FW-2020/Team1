from PoseEstimationImg import *
from ContourDetection import *
import cv2
import time 
import numpy as np

pose = PoseEstimation()
detect = ContourDetection()

img = np.zeros((480,640))
cv2.imwrite('Output-Contour.jpg', img)

points = pose.getPoints()
print(detect.isWithinContour(points, 'Output-Contour.jpg'))