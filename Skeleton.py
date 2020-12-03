"""
Skeleton.py: file to run the program
overall handler for the output to user
@TODO: 
"""
from PoseEstimation import *
from ContourDetection import *
import cv2
import time 
import numpy as np


TIMER_THRESHOLD = 10
WINDOWNAME = 'Hole in the Wall!'
cv2.namedWindow(WINDOWNAME, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(WINDOWNAME,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

# image for testing contour -- can be extended to an array of contours
img = cv2.imread(r'.\test_contour.jpg')
img = cv2.bitwise_not(img)
# _, frame = cap.read()
# print((frame+img).shape)
# cv2.waitKey(0)
# exit(1)
class Skeleton():
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.width  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.PoseEstimator = PoseEstimation() # openPose implementation object
        self.PoseDetector = ContourDetection() # pose detector algorithm created 
        self.user_score = 0
        self.level_number = 1
        self.uservid_weight = 1

    def show_beginning_screen(self):
        frame = np.zeros(shape=[480, 640, 3], dtype=np.uint8)
        txt = ''
        words = ['HOLE ', 'IN ', 'THE ', 'WALL']
        for word in words:
            txt += word
            cv2.putText(frame, txt, (140, 220), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                if cv2.waitKey(500): 
                    break
        cv2.putText(frame, "Press any key to start...", (140, 300), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
        cv2.imshow(WINDOWNAME, frame)
        
        while True:
            if cv2.waitKey(0): 
                break

 
    def editFrame(self,frame, start_time):
        original = np.copy(frame)
        time_remaining = TIMER_THRESHOLD - int(time.perf_counter()-start_time)
        if time_remaining <= 0:
            time_remaining = 0

        if TIMER_THRESHOLD > 7:
            if time_remaining > TIMER_THRESHOLD - 2:
                contour_weight = 0
            elif time_remaining < 2:
                contour_weight = 1
            else:
                contour_weight = 1-(1/(TIMER_THRESHOLD-2)*time_remaining) 
        else:
            contour_weight = 1-(1/(TIMER_THRESHOLD-2)*time_remaining) 

        frame = cv2.addWeighted(frame,self.uservid_weight,img,contour_weight,0)
        cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
        cv2.putText(frame, "Score: {}".format(self.user_score), (500, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)

        return frame, time_remaining, original

    """
    level(number): the code for every level
    input: 
        number -> level that we're on
    output: 
        None. The function does all of the game stuff for us
    @TODO: implement timinig mechanism
    @NOTE: already have some code written for it so I can get this done
    @NOTE: also may be something that'll probably be overridden later 
    """
    def level(self):
        start_time = time.perf_counter()
        frame = np.zeros(shape=[480, 640, 3], dtype=np.uint8)
        cv2.putText(frame, "Level {}".format(self.level_number), (240, 320), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
        cv2.imshow(WINDOWNAME, frame)
        while True:
            time_remaining = 3 - int(time.perf_counter()-start_time)
            if cv2.waitKey(1) == 27 or cv2.waitKey(1) == 63:
                self.__del__()
                exit(0)
            elif cv2.waitKey(0) or time_remaining <= 0: 
                break
            
        total_frames = 0 
        start_time = time.perf_counter()
        while True:
            _, frame = self.cap.read()
            frame, time_remaining, original = self.editFrame(frame, start_time)
            cv2.imshow(WINDOWNAME, frame)
            total_frames += 1
            if cv2.waitKey(1) == ord('q'): 
                break
            elif cv2.waitKey(1) == 27 or cv2.waitKey(1) == 63:
                self.__del__()
                exit(0)
            if time_remaining <= 0: # @TODO
                frame, points = self.PoseEstimator.getPoints(original)
                if self.PoseDetector.isWithinContour(points, 'test_contour.jpg'):
                    self.user_score += 1
                while True:
                    frame, time_remaining, original = self.editFrame(original, start_time) 
                    cv2.imshow(WINDOWNAME, frame)
                    if cv2.waitKey(1) == ord('q'):
                        return
        print(total_frames)
    def _game(self):
        self.show_beginning_screen()
        while True:
            self.level()
            self.level_number += 1
    def __del__(self):
        cv2.destroyAllWindows()
gameSkeleton = Skeleton()
gameSkeleton._game()