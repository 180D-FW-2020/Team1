import cv2
import time
import numpy as np

class PoseEstimation():
    def __init__(self, mode = "MPI", device = "cpu"):
        """
        Initialization function
        """
        self.mode = mode
        # Select model/specify paths
        if self.mode == "MPI":
            protoFile = "pose/mpi/pose_deploy_linevec_faster_4_stages.prototxt"
            weightsFile = "pose/mpi/pose_iter_160000.caffemodel"
            self.nPoints = 15
            self.POSE_PAIRS = [ [0,1],[1,2],[2,3],[3,4],[1,5],[5,6],[6,7],[1,14],[14,8],[8,9],[9,10],[14,11],[11,12],[12,13] ]
        elif self.mode == "COCO":
            protoFile = "pose/coco/pose_deploy_linevec.prototxt"
            weightsFile = "pose/coco/pose_iter_440000.caffemodel"
            self.nPoints = 18
            self.POSE_PAIRS = [ [1,0],[1,2],[1,5],[2,3],[3,4],[5,6],[6,7],[1,8],[8,9],[9,10],[1,11],[11,12],[12,13],[0,14],[0,15],[14,16],[15,17] ]

        # Read network into Memory
        self.net = cv2.dnn.readNetFromCaffe(protoFile, weightsFile)
        if device == "cpu":
            self.net.setPreferableBackend(cv2.dnn.DNN_TARGET_CPU)
            print("Using CPU device")
        elif device == "gpu":
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            print("Using GPU device")

        self.cap = cv2.VideoCapture(0)

    def __readImg(self):
        """
        Read the camera input
        """
        # Read image
        _, self.frame = self.cap.read() # Reading webcam
        self.frameCopy = np.copy(self.frame)
        self.frameWidth = self.frame.shape[1]
        self.frameHeight = self.frame.shape[0]

        t = time.time()
        # Input image dimensions for the network
        inWidth = 368
        inHeight = 368
        # Prepare frame to be fed to network
        inpBlob = cv2.dnn.blobFromImage(self.frame, 1.0 / 255, (inWidth, inHeight), (0, 0, 0), swapRB=False, crop=False)
        # Set prepared object as input blob of network
        self.net.setInput(inpBlob)

        self.output = self.net.forward()
        print("Time taken by network : {:.3f}".format(time.time() - t))

        self.H = self.output.shape[2]
        self.W = self.output.shape[3]
    
    def getPoints(self):
        """
        Returns array of points 
        """
        self.__readImg()

        points = []

        # Plot points on image
        for i in range(self.nPoints):
            # Confidence map of corresponding body's part
            probMap = self.output[0, i, :, :]

            # Find global maxima of the probMap
            minVal, prob, minLoc, point = cv2.minMaxLoc(probMap)
            
            # Scale the point to fit on the original image
            x = (self.frameWidth * point[0]) / self.W
            y = (self.frameHeight * point[1]) / self.H

            threshold = 0.1

            if prob > threshold:
                cv2.circle(self.frameCopy, (int(x), int(y)), 8, (0, 255, 255), thickness=-1, lineType=cv2.FILLED)
                cv2.putText(self.frameCopy, "{}".format(i), (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, lineType=cv2.LINE_AA)

                # Add the point to the list if the probability is greater than the threshold
                points.append((int(x), int(y)))
            else:
                points.append(None)

        return points

    def printPoints(self):
        """
        Outputs OpenPose points to image file
        """
        print(self.getPoints())
        cv2.imshow('Output-Points', self.frameCopy)
        cv2.waitKey(0)
        cv2.imwrite('Output-Points.jpg', self.frameCopy)

    def printSkeleton(self, show = 1):
        """
        Outputs OpenPose skeleton to image file
        """
        points = self.getPoints()
        #print(points)

        # Draw skeleton
        for pair in self.POSE_PAIRS:
            partA = pair[0]
            partB = pair[1]

            if points[partA] and points[partB]:
                cv2.line(self.frame, points[partA], points[partB], (0, 255, 255), 2)
                cv2.circle(self.frame, points[partA], 8, (0, 0, 255), thickness=-1, lineType=cv2.FILLED)
        if show:
            cv2.imshow('Output-Skeleton', self.frame)
            cv2.waitKey(0)
            cv2.imwrite('Output-Skeleton.jpg', self.frame)
        
    def printContour(self):
        """
        Outputs OpenPose contour
        """
        points = self.getPoints()
        print(points)

        img = np.zeros((self.frameHeight,self.frameWidth,3))

        # Draw contour
        for pair in self.POSE_PAIRS:
            partA = pair[0]
            partB = pair[1]

            if points[partA] and points[partB]:
                cv2.line(img, points[partA], points[partB], (255, 255, 255), thickness=75, lineType=cv2.FILLED)
            
        cv2.imshow('Output-Contour', img)
        cv2.waitKey(0) 
        cv2.imwrite('Output-Contour.jpg', img)
    
    def getVideo():
        """
        Returns the video capture
        """
        return self.cap

    def testScoring(self):
        """
        Function to test scoring
        """
        #cap = cv2.VideoCapture(0)
        cap = getVideo()
        w = 640 #cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = 480 #cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(w,h)
        while True:
            #_, frame = cap.read()
            #self.printSkeleton(show=0)
            # start geeksforgeeks https://www.geeksforgeeks.org/python-opencv-cv2-circle-method/
            center_coordinates = (int(w/2), int(h/2)) 
            radius = 100
            color = (255,0,0)
            thickness = 2
            self.frame = cv2.circle(self.frame, center_coordinates, radius, color, thickness)
            cv2.imshow('Output-Points', self.frame)
            if cv2.waitKey(1) == ord('q'):
                break

    def __del__(self):
        """
        Deconstructor method
        """
        #self.cap.release()
        cv2.destroyAllWindows()