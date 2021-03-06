import cv2
import os
import time
import numpy as np

class PoseEstimation():
    SKELETON_LINECOLOR = (236, 183, 76)
    SKELETON_POINTCOLOR = (236, 183, 76)
    def __init__(self, device = "cpu"):
        """
        Constructor
        """
        # self.mode = mode
        # Select model/specify paths
        # if self.mode == "MPI":
        protoFile = os.path.join('pose', 'mpi', 'pose_deploy_linevec_faster_4_stages.prototxt')
        weightsFile = os.path.join('pose', 'mpi', 'pose_iter_160000.caffemodel')
        self.nPoints = 15
        self.POSE_PAIRS = [ [0,1],[1,2],[2,3],[3,4],[1,5],[5,6],[6,7],[1,14],[14,8],[8,9],[9,10],[14,11],[11,12],[12,13] ]
        '''
        elif self.mode == "COCO":
            protoFile = "pose/coco/pose_deploy_linevec.prototxt"
            weightsFile = "pose/coco/pose_iter_440000.caffemodel"
            self.nPoints = 18
            self.POSE_PAIRS = [ [1,0],[1,2],[1,5],[2,3],[3,4],[5,6],[6,7],[1,8],[8,9],[9,10],[1,11],[11,12],[12,13],[0,14],[0,15],[14,16],[15,17] ]
        elif self.mode == "BODY25":
            protoFile = "pose/body_25/pose_deploy.prototxt"
            weightsFile = "pose/body_25/pose_iter_584000.caffemodel"
            self.nPoints = 25
            self.POSE_PAIRS = [ [1,0],[1,2],[1,5],[2,3],[3,4],[5,6],[6,7],[1,8],[8,9],[8,12],[9,10],[10,11],[11,22],[11,24],[12,13],[13,14],[14,19],[14,21],[0,15],[0,16],[15,17],[16,18],[19,20],[22,23] ]
        '''
        # Read network into Memory
        self.net = cv2.dnn.readNetFromCaffe(protoFile, weightsFile)
        if device == "cpu":
            self.net.setPreferableBackend(cv2.dnn.DNN_TARGET_CPU)
            print("Using CPU device")
        elif device == "gpu":
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
            print("Using GPU device")


    """
    getPoints(self, frame, dots=True, dotsVals=False): Return the points from OpenPose 
    input: 
        frame -> the video frame that we want the skeleton to go on top of
        dots -> whether to output dots on each point
        dotsVals -> whether to output values with each point
    output: 
        frame -> the modified frame with the score on it
        points -> the OpenPose output points
    @TODO: 
    @NOTE: 
    @NOTE: 
    """
    def getPoints(self, frame, show=False, dots=True, dotsVals=False):
        inWidth = 640
        inHeight = 480
        inpBlob = cv2.dnn.blobFromImage(frame, 1.0 / 255, (inWidth, inHeight), (0, 0, 0), swapRB=False, crop=False)
        self.net.setInput(inpBlob)
        output = self.net.forward()
        points = []

        # Plot points on image
        for i in range(self.nPoints):
            # Confidence map of corresponding body's part
            probMap = output[0, i, :, :]

            # Find global maxima of the probMap
            minVal, prob, minLoc, point = cv2.minMaxLoc(probMap)
            
            # Scale the point to fit on the original image
            x = (frame.shape[1] * point[0]) / output.shape[3]
            y = (frame.shape[0] * point[1]) / output.shape[2]

            threshold = 0.1

            if prob > threshold:
                if show and dots:
                    cv2.circle(frame, (int(x), int(y)), 8, (0, 255, 255), thickness=-1, lineType=cv2.FILLED)
                    if dotsVals:
                        put = "{}:({}, {})".format(i, int(x), int(y))
                    else:
                        put = "{}".format(i)
                    cv2.putText(frame, put, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, lineType=cv2.LINE_AA)

                # Add the point to the list if the probability is greater than the threshold
                points.append((int(x), int(y)))
            else:
                points.append(None)
        
        if show:
            cv2.imshow('Output-Points', frame)
            cv2.waitKey(0)
            cv2.imwrite('Output-Points.jpg', frame)
        return frame, points


    """
    getSkeleton(self, frame, show = False, lines = False): build the skeleton of points (with the points and lines between them) and, for debugging, show 
    input: 
        frame -> the video frame that we want the skeleton to go on top of
        show -> debugging to show the skeleton only 
    output: 
        frame -> the modified frame with the score on it
        points -> the OpenPose output points
    @TODO: 
    @NOTE: 
    @NOTE: 
    """
    def getSkeleton(self, frame, show = False):
        _, points = self.getPoints(frame)

        # Draw skeleton
        for pair in self.POSE_PAIRS:
            point1 = points[pair[0]]
            point2 = points[pair[1]]

            if point1 and point2:
                cv2.line(frame, tuple(point1), tuple(point2), self.SKELETON_LINECOLOR, 2)
                cv2.circle(frame, tuple(point1), 8, self.SKELETON_POINTCOLOR, thickness=-1, lineType=cv2.FILLED)
        if show:
            cv2.imshow('Output-Skeleton', frame)
            cv2.waitKey(0)
            cv2.imwrite('Output-Skeleton.jpg', frame)

        return frame, points


    """
    getContour(self, frame, show = False): Make the contour
    input: 
        frame -> the video frame that we want the skeleton to go on top of
        show -> debugging to show the skeleton only 
        output -> output file name
    output: 
        frame -> the modified frame with the score on it
        points -> the OpenPose output points
    @TODO: create contour logic 
    """
    def getContour(self, frame, height=480, width=640, show = False, output='Output-Contour.jpg'):
        _, points = self.getPoints(frame)

        img = np.zeros((height, width, 3), np.uint8)

        for pair in self.POSE_PAIRS:
            partA = pair[0]
            partB = pair[1]

            if points[partA] and points[partB]:
                cv2.line(img, points[partA], points[partB], (255, 255, 255), thickness=80, lineType=cv2.FILLED)
        
        if show:
            cv2.imshow('Output-Contour', img)
            cv2.waitKey(0) 
        cv2.imwrite(output, img)

        return frame, points

    """
    getContour(self, points, show = False, output='Output-Contour.jpg'): Make the contour from set of points rather than frame
    input: 
        points -> OpenPose input points
        show -> debugging to show the skeleton only 
    output: 
        img -> the modified frame with the score on it
        points -> the OpenPose output points
    @TODO: create contour logic 
    """
    def getContourFromPoints(self, points, height=480, width=640, show = False, output='Output-Contour.jpg'):
        img = np.zeros((height, width, 3), np.uint8)

        for pair in self.POSE_PAIRS:
            point1 = points[pair[0]]
            point2 = points[pair[1]]

            if point1 and point2:
                cv2.line(img, tuple(point1), tuple(point2), (255, 255, 255), thickness=80, lineType=cv2.FILLED)
        
        if show:
            cv2.imshow('Output-Contour', img) 
            cv2.waitKey(0)
        cv2.imwrite(output, img)
        
        return img, points
        

    def __del__(self):
        """
        Destructor
        """
        cv2.destroyAllWindows()
