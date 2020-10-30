import cv2
import numpy as np
import time as t

class ContourDetection():
    def __init__(self):
        pass
        
    def isWithinContour(self, points, contourfile):
        img = cv2.imread(contourfile, cv2.IMREAD_GRAYSCALE)
        for i in range(len(points)):
            if points[i] != None:
                if img[points[i]] == 0:
                    return False
        return True