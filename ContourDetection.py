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
        points -> Python list of points
        contour -> contour from file system
    output: 
        isWithin -> scaled count of # of points in boundaries
    @TODO: need to work on scaling function, should't take too long 
    @NOTE: accuracy is still around 50%. Need it to increase to about 80+%.
    @NOTE: 
    """
    def isWithinContour(self, points, contour, height=480, width=640):
        count = 0 
        print(points)
        for point in points:
            if point == None or point[1] >= height or point[0] >= width:
                continue
            # print(contour.item(point[1],point[0],0), contour.item(point[1],point[0],1), contour.item(point[1],point[0],2))
            if contour.item(point[1],point[0],0) < 65 and contour.item(point[1],point[0],1) < 65 and contour.item(point[1],point[0],2) < 65:
                count +=1
        return count