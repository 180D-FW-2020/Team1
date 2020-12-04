from PoseEstimation import *
from ContourDetection import *
import cv2
import time
import numpy as np

pose = PoseEstimation()
detect = ContourDetection()

frame = np.zeros(shape=[480, 640, 3], dtype=np.uint8)

pose.getContour(frame, True, 'tPose.jpg')