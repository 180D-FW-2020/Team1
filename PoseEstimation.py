import cv2
import time
import numpy as np

TIMER_THRESHOLD = 3

class PoseEstimation():
    def __init__(self, mode = "MPI", device = "cpu"):
        """
        Constructor
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
        self.score = 0
        # @NOTE would want voice + gesture objects here if possible 
        # @NOTE else we can integrate into rest of code

    """
    getFrame(self): 
    input: 
    output: 
        frame -> the raw camera feed frame
    @TODO: 
    @NOTE: 
    @NOTE: 
    """
    def getFrame(self):
        """
        Read the camera input
        """
        _, frame = self.cap.read() # Reading webcam
        return frame
        
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
                if dots:
                    cv2.circle(frame, (int(x), int(y)), 8, (0, 255, 255), thickness=-1, lineType=cv2.FILLED)
                    if dotsVals:
                        put = "{}:({}, {})".format(i,int(x),int(y))
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
    def getSkeleton(self, frame, show = False, lines = False):
        _, points = self.getPoints(frame)

        # Draw skeleton
        for pair in self.POSE_PAIRS:
            partA = pair[0]
            partB = pair[1]

            if points[partA] and points[partB]:
                if lines:
                    cv2.line(frame, points[partA], points[partB], (0, 255, 255), 2)
                cv2.circle(frame, points[partA], 8, (0, 0, 255), thickness=-1, lineType=cv2.FILLED)
        if show:
            cv2.imshow('Output-Skeleton', frame)
            cv2.waitKey(0)
            cv2.imwrite('Output-Skeleton.jpg', frame)
        return frame, points

    """
    getContour(self, frame, show = False): Make the contour using OpenPose
    input: 
        frame -> the video frame that we want the skeleton to go on top of
        show -> debugging to show the skeleton only 
    output: 
        frame -> the modified frame with the score on it
        points -> the OpenPose output points
    @TODO: create contour logic 
    """
    def getContour(self, frame, show = False):
        _, points = self.getPoints(frame)

        img = np.zeros((480,640))

        for pair in self.POSE_PAIRS:
            partA = pair[0]
            partB = pair[1]

            if points[partA] and points[partB]:
                cv2.line(img, points[partA], points[partB], (255, 255, 255), thickness=80, lineType=cv2.FILLED)
        
        if show:
            cv2.imshow('Output-Contour', img)
            cv2.waitKey(0) 
        cv2.imwrite('Output-Contour.jpg', img)

        return frame, points
    
    """
    scoreTally(self, points, contour): tally the points that a user gets in a specific turn 
    input: 
        points -> the points that openPose returns
        contour -> the contour used for the specific case 
    output: 
        score -> the score for the inputted points + contour combination
    @TODO: implement scoring tally
    """
    def scoreTally(self, points, contour):
        return 0

    """
    showScore(self, frame): show the score
    input: 
        frame -> the video frame that we want the score to go on top of
    output: 
        frame -> the modified frame with the score on it
    @TODO: 
    @NOTE: 
    @NOTE: 
    """
    def showScore(self, frame):
        cv2.putText(frame, "Score: {}".format(self.score), (500, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
        return frame
    
    """
    showTime(self, frame, start_time): show the time remaining  
    input: 
        frame -> the video frame that we want the score to go on top of
    output: 
        frame -> the modified frame with the score on it
    @TODO: implement timinig mechanism
    @NOTE: already have some code written for it so I can get this done
    @NOTE: also may be something that'll probably be overridden later 
    """
    def showTime(self, frame, start_time):
        time_remaining = TIMER_THRESHOLD - int(time.perf_counter()-start_time)
        cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (50, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)

        return frame, time_remaining
    
    """
    startUI(self): the overall handler for the output to user  
    input: 
        NONE
    output: 
        NONE
    @TODO: create overall skeleton of function @NOTE DONE 
    @TODO: figure out how to add contours (DONE), voice/speech, gesture into it
    @TODO: shown below: want to have a UI change while the score is being tallied 
    @TODO: go to the "next level"
    @NOTE: consider cv2.waitKey(0) 
    """
    def startUI(self):
        start_time = time.perf_counter()
        while True:
            _, frame = self.cap.read()
            frame = self.showContours(frame)
            frame = self.showScore(frame)
            frame, time_remaining = self.showTime(frame, start_time)
            cv2.imshow('Hole in the Wall!', frame)
            if cv2.waitKey(1) == ord('q'): 
                break
            if time_remaining <= 0: # @TODO
                frame, points = self.buildSkeleton(frame)
                while True:
                    cv2.imshow('Hole in the Wall!', frame)
                    if cv2.waitKey(1) == ord('q'):
                        return # actually want to go to the next one 

    def __del__(self):
        """
        Destructor
        """
        self.cap.release()
        cv2.destroyAllWindows()
