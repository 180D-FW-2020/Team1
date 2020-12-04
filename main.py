"""
game.py: file to run the program
overall handler for the output to user
@TODO: 
"""
from PoseEstimation import *
from ContourDetection import *
from voice import *
import cv2
import time 
import numpy as np
import random


DEBUG = 0

TIMER_THRESHOLD = 10
ZERO_KEY = 48
ONE_KEY = 49
ESC_KEY = 27
WINDOWNAME = 'Hole in the Wall!'
cv2.namedWindow(WINDOWNAME, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(WINDOWNAME,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

def ex1():
    print("activate command called")
def ex2():
    print("help command called")

command_dict = {
    "activate" : ex1,
    "help" : ex2
}

contour_file_names = [r'.\test_contour.jpg']
contour_pictures = []
for contour_file in contour_file_names:
    img = cv2.imread(contour_file)
    img = cv2.bitwise_not(img)
    contour_pictures.append(img)

class Game():
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.width  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.PoseEstimator = PoseEstimation() # openPose implementation object
        self.PoseDetector = ContourDetection() # pose detector algorithm created \
        self.voice = commandRecognizer(command_dict)
        self.user_score = 0
        self.level_number = 0
        self.uservid_weight = 1
        self.mode = -1 # 0 for single player, 1 for multi player
        self.voice.listen()

    def show_screen(self, screen_type):
        frame = np.zeros(shape=[480, 640, 3], dtype=np.uint8)
        txt = ''
        if screen_type == 'start':
            words = ['HOLE ', 'IN ', 'THE ', 'WALL']
        elif screen_type == 'level':
            words = ['LEVEL ', '{}'.format(self.level_number)]
        elif screen_type == 'level_end':
            words = ['Level End']
        for word in words:
            txt += word
            cv2.putText(frame, txt, (140, 220), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                if cv2.waitKey(500): 
                    break
        if screen_type == 'start':
            cv2.putText(frame, "Press 0 for single player and 1 for multi player...", (140, 300), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(0)
                if key == ZERO_KEY:
                    self.mode = 0
                    break
                elif key == ONE_KEY:
                    self.mode = 1
                    break 
                elif key == ESC_KEY:
                    self.__del__()
                    exit(0)
        elif screen_type == 'level':
            cv2.putText(frame, "Press any key to start.", (140, 300), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(0)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key > 0: 
                    break
        elif screen_type == 'level_end':
            cv2.putText(frame, "Score: {}".format(self.user_score), (140, 300), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(0)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key > 0: 
                    break
 
    def editFrame(self, frame, start_time, contour, override_time = False):
        original = np.copy(frame)
        time_remaining = TIMER_THRESHOLD - int(time.perf_counter()-start_time)
        if time_remaining <= 0 or override_time == True:
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

        frame = cv2.addWeighted(frame,self.uservid_weight,contour,contour_weight,0)
        ######### start powerup code 
        powerup = cv2.imread(r'.\powerup.jpg')
        rows1,cols1,channels1 = powerup.shape
        rows2,cols2,channels2 = frame.shape
        roi = frame[(rows2-rows1):rows2, (cols2-cols1):cols2 ]

        # Now create a mask of logo and create its inverse mask also
        powerupgray = cv2.cvtColor(powerup,cv2.COLOR_BGR2GRAY)
        ret, mask = cv2.threshold(powerupgray, 10, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)

        # Now black-out the area of logo in ROI
        frame_bg = cv2.bitwise_and(roi,roi,mask = mask_inv)

        # Take only region of logo from logo image.
        powerup_fg = cv2.bitwise_and(powerup,powerup,mask = mask)

        # Put logo in ROI and modify the main image
        dst = cv2.add(frame_bg,powerup_fg)
        frame[(rows2-rows1):rows2, (cols2-cols1):cols2 ] = dst
        ######### stop powerup code 
        cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
        cv2.putText(frame, "Score: {}".format(self.user_score), (500, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
        # print('time remaining', time_remaining)
        return frame, time_remaining, original

    """
    singleplayer():
    input: 
        None
    output: 
        None. The function does all of the game stuff for us
    @TODO: still need to improve UI 
    @TODO: need a better contour detection algorithm 
    @TODO: create a function to restart game at any point 
    @NOTE: 
    """
    def singleplayer(self):
        while True:
            self.level_number += 1
            self.level()
    def level(self):
        contour_num = random.randint(0,len(contour_pictures)-1)
        contour = contour_pictures[contour_num]
        frame = np.zeros(shape=[480, 640, 3], dtype=np.uint8)
        self.show_screen('level')
        start_time = time.perf_counter()
        print(start_time)
        override_time=False
        stop = False
        while True:
            key = cv2.waitKey(1)
            if key == ESC_KEY:
                self.__del__()
                exit(0)
            elif key == ord('s'):
                override_time = True
            # elif key == ord('m'):
            #     self.game()
            
            _, frame = self.cap.read()
            frame, time_remaining, original = self.editFrame(frame, start_time, contour, override_time=override_time)
            cv2.imshow(WINDOWNAME, frame)
            if override_time == True and stop == False:
                start_time+=1
                stop = True
                continue
            if time_remaining <= 0: 
                frame, time_remaining, original = self.editFrame(frame, start_time, contour, override_time=override_time)
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(100):
                        break
                frame, points = self.PoseEstimator.getPoints(original)
                level_score = self.PoseDetector.isWithinContour(points, contour)
                if DEBUG:
                    cv2.imshow(WINDOWNAME, frame)
                    while True:
                        if cv2.waitKey(0):
                            break
                self.user_score += level_score
                self.show_screen('level_end')
                return
    """
    multiplayer(self): gameplay for the multiplayer version
    @TODO: require a lot of work in this implementation. So far, I've only worked on the contour detection part of it 
    """
    def multiplayer(self):
        pass
    def game(self):
        self.show_screen('start')
        if self.mode == 0:
            self.singleplayer()
        elif self.mode == 1: 
            self.multiplayer()
        else:
            print('error')
            exit(1)
    def test(self):
        frame = np.zeros(shape=[480, 640, 3], dtype=np.uint8)
        example_arr = [None, (352, 296), (320, 296), None, None, (416, 160), (296, 112), (256, 120), (352, 120), None, None, (488, 168), None, None, (440, 160)]
        output = contour_pictures[0]
        count = 0 
        for point in example_arr:
            if point == None or point[0] > 480 or point[1] > 640:
                continue
                # cv2.circle(output, (point[0],point[1]), 8, (0, 255, 255), thickness=-1, lineType=cv2.FILLED)
            if output[point[0],point[1],0] > 20 and output[point[0],point[1],1] > 20 and output[point[0],point[1],2] > 20:
                count +=1
        for point in example_arr:
            if point != None:
                cv2.circle(output, (point[0],point[1]), 8, (0, 255, 255), thickness=-1, lineType=cv2.FILLED)
        print(count)
        cv2.imshow('test',output)
        while True:
            if cv2.waitKey(0):
                break
    def testVision(self):
        pose = PoseEstimation()
        detect = ContourDetection()
        frame = pose.getFrame()
        pose.getSkeleton(frame, True, True)       
    def __del__(self):
        cv2.destroyAllWindows()

if __name__ == '__main__':
    gameSkeleton = Game()
    gameSkeleton.game()
