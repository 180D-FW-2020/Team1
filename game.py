"""
game.py: file to run the program
overall handler for the output to user
@TODO: 
"""
from PoseEstimation import *
from ContourDetection import *
from voice import *
from mqtt import *
import cv2
import time 
import numpy as np
import random
import os

DEBUG = 0 # 1 to see all the contours, 2 to see the points after contour detection 

ENTER_KEY = 13
ESC_KEY = 27
UP_KEY = 38
DOWN_KEY = 40
ZERO_KEY = 48
ONE_KEY = 49


WINDOWNAME = 'Hole in the Wall!'
GRAPHICS = '.\graphics\\'
POSES = 'poses\\'
POWERUPS = 'powerups\\'
PATH = GRAPHICS + POSES
DIFFICULTIES = ['easy\\', 'medium\\', 'hard\\']
cv2.namedWindow(WINDOWNAME, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(WINDOWNAME,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

powerup_pictures = {}
powerup_dir = GRAPHICS + POWERUPS
power_up_file_names = os.listdir(powerup_dir)
for powerup_file_name in power_up_file_names:
    powerup = cv2.imread(powerup_dir + powerup_file_name)
    powerup_pictures[powerup_file_name] = powerup
    
easy_contours = []
medium_contours = []
hard_contours = []
for difficulty in DIFFICULTIES:
    cur_dir = PATH + difficulty
    for contour_file in os.listdir(cur_dir):
        img = cv2.imread(cur_dir + contour_file)
        img = cv2.bitwise_not(img)
        if difficulty == 'easy\\':
            easy_contours.append(img)
        if difficulty == 'medium\\':
            medium_contours.append(img)
        if difficulty == 'hard\\':
            hard_contours.append(img)
contour_pictures = []
contour_pictures.extend(easy_contours)
contour_pictures.extend(medium_contours)
contour_pictures.extend(hard_contours)
if DEBUG == 1:
    print(len(contour_pictures))
    for picture in contour_pictures:
        cv2.imshow('test', picture)
        cv2.waitKey(0)

class Game():
    
    def __init__(self):
        # Capturing Video
        self.cap = cv2.VideoCapture(0)
        self.width  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # OpenPose
        self.PoseEstimator = PoseEstimation() # openPose implementation object
        self.PoseDetector = ContourDetection() # pose detector algorithm created 
        
        # Voice
        self.command_dict = {   
            "activate" : self.activate,
            "help" : self.help
        }
        self.voice = commandRecognizer(self.command_dict)
        self.voice.listen()

        # MQTT
        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_message = on_message
        self.client.connect_async('mqtt.eclipse.org') # 2. connect to a broker using one of the connect*() functions.
        self.client.loop_start() # 3. call one of the loop*() functions to maintain network traffic flow with the broker.

        # User variables
        self.user_score = 0
        self.level_number = 0
        self.uservid_weight = 1
        self.mode = -1 # 0 for single player, 1 for multi player
        self.difficulty = -1 # 0 for easy, 1 for medium, 2 for hard
        self.TIMER_THRESHOLD = 5
        
        self.powerup_vals = {} 
        for powerup_file_name in power_up_file_names:
            self.powerup_vals[powerup_file_name] = 2
        # self.powerup_vals['speed up'] = 2
        # self.powerup_vals['slow down'] = 2
        self.speed_up_used = False
        self.slow_down_used = False
        
    def activate(self):
        print("activate command called")
        if self.powerup_vals[power_up_file_names[0]] > 0:
            self.powerup_vals[power_up_file_names[0]] -= 1
            self.speed_up_used = True

    def help(self):
        print("help command called")   
        if self.powerup_vals[power_up_file_names[1]] > 0:
            self.powerup_vals[power_up_file_names[1]] -= 1
            self.slow_down_used = True

    def show_screen(self, screen_type, points = 0):
        frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
        txt = ''
        if screen_type == 'start':
            words = ['HOLE ', 'IN ', 'THE ', 'WALL']
            for word in words:
                txt += word
                cv2.putText(frame, txt, (140, 220), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(500): 
                        break
            cv2.putText(frame, "Single Player Mode --- Enter", (175, 300), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Two-Player Mode ---- 1", (175, 350), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.putText(frame, "-->",(135,300), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            
            while True:
                key = cv2.waitKey(0)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key == ENTER_KEY:
                    if self.mode == -1:
                        self.mode = 0
                    break
                elif key == ONE_KEY:
                    if self.mode != -1 and self.mode != 0:
                        continue
                    self.mode = 1
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, txt, (140, 220), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Single Player Mode --- 0", (175, 300), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Two-Player Mode ---- Enter", (175, 350), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,350), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                elif key == ZERO_KEY:
                    if self.mode == 0:
                        continue
                    self.mode = 0
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, txt, (140, 220), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Single Player Mode --- Enter", (175, 300), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Two-Player Mode ---- 1", (175, 350), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,300), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                
        elif screen_type == 'level':
            words = ['LEVEL ', '{}'.format(self.level_number)]        
            for word in words:
                txt += word
                cv2.putText(frame, txt, (140, 220), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(500): 
                        break
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
            words = ['Level End']
            for word in words:
                txt += word
                cv2.putText(frame, txt, (140, 220), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(500): 
                        break
            if self.speed_up_used:
                cv2.putText(frame, "DOUBLE POINTS!!", (140, 300), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.putText(frame, "This round: {} points".format(points), (140, 350), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Overall: {} points".format(self.user_score), (140, 400), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(0)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key > 0: 
                    break
        elif screen_type == 'difficulty':
            cv2.putText(frame, 'Select a difficulty:', (140, 220), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Easy --- Press \'e\'", (175, 300), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Medium --- Press \'m\'", (175, 350), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Hard --- Press \'h\'", (175, 400), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(0)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key == ord('e'):
                    self.difficulty = 0
                    break
                elif key == ord('m'):
                    self.difficulty = 1
                    break
                elif key == ord('h'):
                    self.difficulty = 2
                    break
            
            

    def editFrame(self, frame, start_time, contour, override_time = False):
        original = np.copy(frame)
        time_elapsed = int(time.perf_counter()-start_time)
        time_remaining = self.TIMER_THRESHOLD - time_elapsed
        if time_remaining <= 0 or override_time == True:
            time_remaining = 0

        if time_elapsed < self.TIMER_THRESHOLD*.2: #80% --> want no opacity
            contour_weight = 0
        elif time_elapsed > self.TIMER_THRESHOLD*.8: #20% --> want full opacity
            contour_weight = 1
        else:
            contour_weight = 5.0/(3.0*self.TIMER_THRESHOLD)*(time_elapsed-0.2*self.TIMER_THRESHOLD)+1.0/3.0 # grab a weight based on the time that's elapsed 

        frame = cv2.addWeighted(frame,self.uservid_weight,contour,contour_weight,0)
        num = 1
        
        for powerup_file_name in power_up_file_names:
            powerup = powerup_pictures[powerup_file_name]
            powerup_num_left = self.powerup_vals[powerup_file_name]
            row_bias = num*60 + 40
            col_bias = 20
            rows1,cols1,channels1 = powerup.shape
            rows2,cols2,channels2 = frame.shape
            # print(rows2-rows1- row_bias, rows2-row_bias)
            # print((cols2-cols1-col_bias),(cols2-col_bias))
            row_1 = rows2 - rows1 - row_bias
            row_2 = rows2 - row_bias
            col_1 = cols2 - cols1 - col_bias
            col_2 = cols2 - col_bias
            roi = frame[(row_1):(row_2), (col_1):(col_2) ]
            powerupgray = cv2.cvtColor(powerup,cv2.COLOR_BGR2GRAY)
            ret, mask = cv2.threshold(powerupgray, 10, 255, cv2.THRESH_BINARY)
            mask_inv = cv2.bitwise_not(mask)
            frame_bg = cv2.bitwise_and(roi,roi,mask = mask_inv)
            powerup_fg = cv2.bitwise_and(powerup,powerup,mask = mask)
            dst = cv2.add(frame_bg,powerup_fg)
            frame[(row_1):(row_2), (col_1):(col_2) ] = dst
            cv2.putText(frame, '{} x'.format(powerup_num_left), (640-110, 480-row_bias-20), cv2.FONT_HERSHEY_COMPLEX, .5, (255, 50, 0), 2, lineType=cv2.LINE_AA)
            num+=1
        
        cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
        cv2.putText(frame, "Score: {}".format(self.user_score), (500, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
        # print('time remaining', time_remaining)
        return frame, time_remaining, original

    def level(self):
        timer_old = self.TIMER_THRESHOLD
        
        if self.difficulty == 0:
            contour_num = random.randint(0,len(easy_contours)-1)
            contour = easy_contours[contour_num]
        elif self.difficulty == 1:
            contour_num = random.randint(0,len(medium_contours)-1)
            contour = medium_contours[contour_num]
        if self.difficulty == 2:
            contour_num = random.randint(0,len(hard_contours)-1)
            contour = hard_contours[contour_num]
        frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
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
            elif key == ord('s') or self.speed_up_used == True:
                override_time = True
            # elif key == ord('m'):
            #     self.game()
            if self.slow_down_used == True:
                self.TIMER_THRESHOLD *= 2
                self.slow_down_used = False
                
            _, frame = self.cap.read()
            frame, time_remaining, original = self.editFrame(frame, start_time, contour, override_time=override_time)
            cv2.imshow(WINDOWNAME, frame)
            if override_time == True and stop == False:
                start_time+=1
                stop = True
                continue
            if time_remaining <= 0: 
                self.TIMER_THRESHOLD = timer_old
                frame, time_remaining, original = self.editFrame(frame, start_time, contour, override_time=override_time)
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(100):
                        break
                frame, points = self.PoseEstimator.getPoints(original)
                level_score = self.PoseDetector.isWithinContour(points, contour)
                if DEBUG == 2:
                    cv2.imshow(WINDOWNAME, frame)
                    while True:
                        if cv2.waitKey(0):
                            break
                if self.speed_up_used:
                    level_score *= 2
                self.user_score += level_score
                self.show_screen('level_end',points=level_score)
                return


    def singleplayer(self):
        while self.difficulty == -1:
            self.show_screen('difficulty')
        while True:
            self.level_number += 1
            self.slow_down_used = False
            self.speed_up_used = False
            
            self.level()
            if self.TIMER_THRESHOLD > 5:
                self.TIMER_THRESHOLD -= 2


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
        frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
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

    def __del__(self):
        cv2.destroyAllWindows()
        self.client.loop_stop()
        self.client.disconnect()
        self.voice.stop()

def main():
    game = Game()
    game.game()

if __name__ == '__main__':
    main()