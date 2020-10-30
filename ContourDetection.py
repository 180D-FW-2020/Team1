import cv2
import numpy as np
import time as t

class ContourDetection():
    def __init__(self):
        """
        Initialize function
        """
        pass
        
    def isWithinContour(self, points, contourfile):
        """
        Returns True if OpenPose output points are within given contour 
            from file
        """
        img = cv2.imread(contourfile, cv2.IMREAD_GRAYSCALE)
        for i in range(len(points)):
            if points[i] != None:
                if img[points[i]] == 0:
                    return False
        return True