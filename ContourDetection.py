import cv2
import numpy as np
import time as t

class ContourDetection():
    def __init__(self):
        """
        Initialize function
        """
        pass
    
    """
    isWithinContour(self, points, contourfile): Output 
    input: 
        points -> OpenPose output array of points
        contourfile -> OpenPose output of contour from file
    output: 
        isWithin -> Boolean whether or not points are within contour
    @TODO: 
    @NOTE: 
    @NOTE: 
    """
    def isWithinContour(self, points, contourfile):
        img = cv2.imread(contourfile, cv2.IMREAD_GRAYSCALE)
        for i in range(len(points)):
            if points[i] != None:
                if img[points[i]] == 0:
                    return False
        return True