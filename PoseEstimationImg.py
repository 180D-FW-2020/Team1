import cv2
import time
import numpy as np
import argparse
import math

POINTS = 'points'
NPY = '.npy'
DEBUG = 'debug'

OFFSET = 10 # some predefined arbitrary number 

""" parser = argparse.ArgumentParser(description='Run keypoint detection')
parser.add_argument("--device", default="cpu", help="Device to inference on")
parser.add_argument("--image_file", default="single.jpeg", help="Input image")
parser.add_argument("--debug", default='', help="Debugging or not")

args = parser.parse_args() """

class PoseEstimation():
    def __init__(self, mode = "MPI", device = "cpu"):
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
        # Read image
        #frame = cv2.imread(args.image_file)
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
    
    def __getPoints(self):
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
        print(self.__getPoints())
        cv2.imshow('Output-Points', self.frameCopy)
        cv2.waitKey(0)
        cv2.imwrite('Output-Points.jpg', self.frameCopy)

    def printSkeleton(self):
        points = self.__getPoints()
        print(points)

        # Draw skeleton
        for pair in self.POSE_PAIRS:
            partA = pair[0]
            partB = pair[1]

            if points[partA] and points[partB]:
                cv2.line(self.frame, points[partA], points[partB], (0, 255, 255), 2)
                cv2.circle(self.frame, points[partA], 8, (0, 0, 255), thickness=-1, lineType=cv2.FILLED)

        cv2.imshow('Output-Skeleton', self.frame)
        cv2.waitKey(0)
        cv2.imwrite('Output-Skeleton.jpg', self.frame)
    
    def printContour(self):
        points = self.__getPoints()
        print(points)

        img = np.zeros((self.frameHeight,self.frameWidth,3))

        # Draw contour
        for pair in self.POSE_PAIRS:
            partA = pair[0]
            partB = pair[1]

            if points[partA] and points[partB]:
                cv2.line(img, points[partA], points[partB], (255, 255, 255), thickness=90, lineType=cv2.FILLED)
            
        cv2.imshow('Output-Contour', img)
        cv2.waitKey(0) 
        cv2.imwrite('Output-Contour.jpg', img)

    def __del__(self):
        self.cap.release()
        cv2.destroyAllWindows()

"""
# Select model/specify paths
MODE = "MPI"

if MODE == "COCO":
    protoFile = "pose/coco/pose_deploy_linevec.prototxt"
    weightsFile = "pose/coco/pose_iter_440000.caffemodel"
    nPoints = 18
    POSE_PAIRS = [ [1,0],[1,2],[1,5],[2,3],[3,4],[5,6],[6,7],[1,8],[8,9],[9,10],[1,11],[11,12],[12,13],[0,14],[0,15],[14,16],[15,17]]

elif MODE == "MPI" :
    protoFile = "pose/mpi/pose_deploy_linevec_faster_4_stages.prototxt"
    weightsFile = "pose/mpi/pose_iter_160000.caffemodel"
    nPoints = 15
    POSE_PAIRS = [ [0,1], [1,2], [2,3], [3,4], [1,5], [5,6], [6,7], [1,14], [14,8], [8,9], [9,10], [14,11], [11,12], [12,13] ]

# Read image
#frame = cv2.imread(args.image_file)
_, frame = cv2.VideoCapture(0).read() # Reading webcam
frameCopy = np.copy(frame)
frameWidth = frame.shape[1]
frameHeight = frame.shape[0]
threshold = 0.1

# Read network into Memory
net = cv2.dnn.readNetFromCaffe(protoFile, weightsFile)

if args.device == "cpu":
    net.setPreferableBackend(cv2.dnn.DNN_TARGET_CPU)
    print("Using CPU device")
elif args.device == "gpu":
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
    print("Using GPU device")

t = time.time()
# Input image dimensions for the network
inWidth = 368
inHeight = 368
# Prepare frame to be fed to network
inpBlob = cv2.dnn.blobFromImage(frame, 1.0 / 255, (inWidth, inHeight), (0, 0, 0), swapRB=False, crop=False)
# Set prepared object as input blob of network
net.setInput(inpBlob)

output = net.forward()
print("time taken by network : {:.3f}".format(time.time() - t))

H = output.shape[2]
W = output.shape[3]

# Empty list to store the detected keypoints
points = []

# Plot points on image
for i in range(nPoints):
    # Confidence map of corresponding body's part
    probMap = output[0, i, :, :]

    # Find global maxima of the probMap
    minVal, prob, minLoc, point = cv2.minMaxLoc(probMap)
    
    # Scale the point to fit on the original image
    x = (frameWidth * point[0]) / W
    y = (frameHeight * point[1]) / H

    if prob > threshold: 
        cv2.circle(frameCopy, (int(x), int(y)), 8, (0, 255, 255), thickness=-1, lineType=cv2.FILLED)
        cv2.putText(frameCopy, "{}".format(i), (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, lineType=cv2.LINE_AA)

        # Add the point to the list if the probability is greater than the threshold
        points.append((int(x), int(y)))
    else:
        points.append(None)

# Draw skeleton
for pair in POSE_PAIRS:
    partA = pair[0]
    partB = pair[1]

    if points[partA] and points[partB]:
        cv2.line(frame, points[partA], points[partB], (0, 255, 255), 2)
        cv2.circle(frame, points[partA], 8, (0, 0, 255), thickness=-1, lineType=cv2.FILLED)

# uncomment to see visual output
#cv2.imshow('Output-Keypoints', frameCopy) 
#cv2.imshow('Output-Skeleton', frame) 
#cv2.waitKey(0)

print(points)

points = np.array(points)

# if we're debugging, save the current one as pointsdebug.npy and the previous one remains as points.npy
if args.debug == '':
    np.save(POINTS + NPY, points, allow_pickle=True) # allow_pickle=False is for security 
    new_points = np.load(POINTS + DEBUG + NPY , allow_pickle=True) # allow_pickle=False is for security 
    cv2.imwrite('Output-Keypoints-debug.jpg', frameCopy)
    cv2.imwrite('Output-Skeleton-debug.jpg', frame)
elif args.debug == 'Y':
    np.save(POINTS + DEBUG + NPY , points, allow_pickle=True) # allow_pickle=False is for security 
    new_points = np.load(POINTS + NPY, allow_pickle=True) # allow_pickle=False is for security 
    cv2.imwrite('Output-Keypoints.jpg', frameCopy)
    cv2.imwrite('Output-Skeleton.jpg', frame)
distance = 0
for i in range(len(new_points)):
    if (points[i] == None and new_points[i] != None) or (points[i] != None and new_points[i] == None):
        distance += OFFSET #arbitrary, subject to change
    elif points[i] != None and new_points[i] != None:
        distance += math.sqrt((points[i][0]-new_points[i][0])**2+(points[i][1]-new_points[i][1])**2) #euclidian 

print("Total \"distance\" from regular picture to debug picture is {}".format(distance))
print("Total time taken : {:.3f}".format(time.time() - t)) """