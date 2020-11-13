from PoseEstimation import *
from ContourDetection import *
import cv2
import time
import numpy as np

pose = PoseEstimation()
detect = ContourDetection()

frame = pose.getFrame()

pose.getSkeleton(frame, True, True)