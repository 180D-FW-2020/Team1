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
        img = cv2.imread(contourfile, cv2.COLOR_BGR2GRAY)
        print(points)
        for point in points:
            if point == None:
                continue
                if img[point[0],point[1]] == 255:
                    print("False")
                    return False
        print("True")
        return True