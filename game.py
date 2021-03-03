"""
game.py: file to run the program
overall handler for the output to user
"""
from PoseEstimation import *
from ContourDetection import *
from voice import *
from connect import *
# from mqtt import *
import cv2
import time 
import numpy as np
import random
import os
import platform
import paho.mqtt.client as mqtt
import json
import boto3
from botocore.config import Config
from botocore.client import ClientError
import threading
import key

region='us-east-1'
ROOM = 'ece180d-team1-room-'

OS = platform.system()

FONTCOLORWHITE = (255,255,255)
FONTCOLORBLACK = (0,0,0)
FONTCOLORDEFAULT = (236, 183, 76) ## blue
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONTSIZE = 1
FONTSCALE = 0.8

ACCESS_KEY = key.ACCESS_KEY
SECRET_KEY = key.SECRET_KEY

try:
    ip = key.ip 
    port = key.port
    user = key.user 
    password = key.password
    raspi = True 
except AttributeError:
    ip = ''
    port = ''
    user = ''
    password = ''
    raspi = False 
    print('No Raspberry Pi detected, check key.py to verify connection information.')

# DEBUG: 
# 0 for regular
# 1 to see all the contours
# 2 to see the points after contour detection
# 3 for testing the pause button
DEBUG = 0

# KEY Definitions
BACK_KEY = 8
ENTER_KEY = 13
ESC_KEY = 27
UP_KEY = 38
DOWN_KEY = 40
ZERO_KEY = 48
ONE_KEY = 49
TWO_KEY = 50
THREE_KEY = 51 

# WINDOW Definition 
WINDOWNAME = 'Hole in the Wall!'
if(OS == 'Darwin'): 
    cv2.namedWindow(WINDOWNAME, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(WINDOWNAME,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
else:
    cv2.namedWindow(WINDOWNAME, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(WINDOWNAME,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

MAC_ASPECT_RATIO = (720, 1280)

# FILESYSTEM Definitions 
GRAPHICS = os.path.join(os.path.curdir, 'graphics')
POSES = os.path.join(GRAPHICS, 'poses')
POWERUPS = os.path.join(GRAPHICS, 'powerups')
DIFFICULTIES = [os.path.join(POSES, 'easy'), os.path.join(POSES, 'medium'), os.path.join(POSES, 'hard')]

# FILESYSTEM Work 
powerup_pictures = {}
power_up_file_names = os.listdir(POWERUPS)
for powerup_file_name in power_up_file_names:
    powerup = cv2.imread(os.path.join(POWERUPS, powerup_file_name))
    powerup_pictures[powerup_file_name] = powerup
    
easy_contours = []
medium_contours = []
hard_contours = []
for difficulty in DIFFICULTIES:
    for contour_file in os.listdir(difficulty):
        img = cv2.imread(os.path.join(difficulty, contour_file))
        img = cv2.bitwise_not(img)
        if OS == 'Darwin':
            img = cv2.resize(img, MAC_ASPECT_RATIO)
        if difficulty == os.path.join(POSES, 'easy'):
            easy_contours.append(img)
        if difficulty == os.path.join(POSES, 'medium'):
            medium_contours.append(img)
        if difficulty == os.path.join(POSES, 'hard'):
            hard_contours.append(img)
contour_pictures = []
contour_pictures.extend(easy_contours)
contour_pictures.extend(medium_contours)
contour_pictures.extend(hard_contours)
if DEBUG == 1:
    print(len(contour_pictures))
    for picture in easy_contours:
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
            "easy" : self.change_diff,
            "medium" : self.change_diff,
            "hard" : self.change_diff,
            "single" : self.change_mode,
            "multi" : self.change_mode,
            "tutorial" : self.change_mode,
            "calibrate" : self.change_mode,
            "start" : self.enter_sent,
            "enter" : self.enter_sent,
            "begin" : self.enter_sent
        }
        self.voice = commandRecognizer(self.command_dict)
        self.voice.listen()

        # MQTT
        self.client_mqtt = mqtt.Client()
        self.client_mqtt.on_connect = self.on_connect
        self.client_mqtt.on_disconnect = self.on_disconnect
        self.client_mqtt.on_message = self.on_message
        self.client_mqtt.connect_async('broker.hivemq.com') # 2. connect to a broker using one of the connect*() functions.
        self.client_mqtt.loop_start() # 3. call one of the loop*() functions to maintain network traffic flow with the broker.
        self.users = {}
        self.num_users = 0

        # Raspberry Pi 
        if raspi: 
            self.remote_connection = rpi_conn(ip, port, user, password)
            x = threading.Thread(target = self.remote_connection.connect, daemon=True)
            x.start()

        # powerups
        self.powerup_vals = {} 
        for powerup_file_name in power_up_file_names:
            self.powerup_vals[powerup_file_name] = 0
        # self.powerup_vals['speed up'] = 2
        # self.powerup_vals['slow down'] = 2
        self.speed_up_used = False
        self.slow_down_used = False
        
        #AWS 
        my_config = Config(
            region_name = region
        )

        self.client_aws = boto3.client(
            's3',
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY
        )
        self.room = ['*','*','*','*','*','*']
        self.password = []
        self.true_pass = ''
        self.nickname = []
        self.bucket = None
        self.creator = 0 # 1 for creator, 0 for joiner 
        self.room_name = '' 
        self.multi_start = 0 # 1 to start game (creator tells the rest)

        # User variables
        self.user_score = 0
        self.level_number = 0
        self.uservid_weight = 1
        self.mode = -1 # 0 for single player, 1 for multi player, 2 for tutorial, 3 for calibration 
        self.enter_pressed = False
        self.difficulty = -1 # 0 for easy, 1 for medium, 2 for hard
        self.TIMER_THRESHOLD = 20
        self.play = False
        self.reset_timer = -1

        # multiplayer user variables
        self.send_my_pose = 0 #1 means I'm the pose leader --> local user makes a pose
        self.move_on = 1 #1 means round is over, creator chooses next pose leader --> CREATOR only 
        self.pose_updated = 0 #1 means pose leader sent pose over mqtt --> ALL users should fit in hole 
        self.waiting_for_others = 0 #1 means that we (local user is pose leader) have sent our pose across and are waiting for others to finish fitting inside the hole 
        self.pose = [] # the pose we received from the pose leader 
        self.next_leader = 0 #1 means next leader has been chosen, move on to pose stuff
        self.level_score = 0
        self.score_received = 0
        self.pose_leader = ''
        self.round_scores = {} # creator keeps track of who got what score that specific round -- emptied after each round ends 
        self.total_scores = {} # creator keeps track of who has what score ovreal -- never empties 
                               # NOTE indexing should be same for round_scores and total_scores
        self.multi_powerups = ['double_points', 'mirror', 'lights_out']
        """ powerup list for multiplayer:
        1. double_points: for pose leader -- gets 2*(15-average of other people's scores) for the round
        2. mirror: mirror's posers' camera and contour 
        3. lights_out: blacks out posers' camera
        """
        self.multi_gesture_names = ['double tap','tap','wave']
        self.multi_description = ['Hopefully your pose was too hard for em!',
        'You mirrored your opponents\' screens!',
        'You turned off their cameras!'
        ]
        self.generated_powerup = ''
        self.current_powerup = ''
        self.current_description = ''
        self.powerup_used = 0
        self.round_num = 0
        self.max_multi_score_round = -1
        self.round_score_leader = ''
        self.display_pictures = 0
        self.lobby_users = []
        
    def on_connect(self, client, userdata, flags, rc):
        print("Connection returned result: "+str(rc))
        
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print('Unexpected Disconnect')
        else:
            print('Expected Disconnect')

    def on_gesture(self, gesture, user = ''):
        if self.mode == 0:
            if gesture == 'wave':
                # add 1 to activate powerup count 
                if self.play == False:
                    return
                if self.powerup_vals[power_up_file_names[0]] < 3:
                    self.powerup_vals[power_up_file_names[0]] += 1
                else:
                    pass # try to add more points for the level 
            elif gesture == 'tap':
                # add 1 to help powerup count 
                if self.play == False:
                    return
                if self.powerup_vals[power_up_file_names[1]] < 3:
                    self.powerup_vals[power_up_file_names[1]] += 1
                else:
                    pass # try to add more points for the level 
            elif gesture == 'double_tap':
                # pause/un-pause
                if self.play:
                    self.play = False
                    self.reset_timer = time.perf_counter()
                else:
                    self.play = True
                    self.TIMER_THRESHOLD += int(time.perf_counter() - self.reset_timer)
                    self.reset_timer = -1
        else: 
            if user != self.nickname:
                return
            if gesture == 'wave':
                if self.generated_powerup == 'lights_out':
                    self.current_powerup = self.generated_powerup
                    self.powerup_used = 1
            elif gesture == 'tap':
                if self.generated_powerup == 'mirror':
                    self.current_powerup = self.generated_powerup
                    self.powerup_used = 1
            elif gesture == 'double_tap':
                if self.generated_powerup == 'double_points':
                    self.current_powerup = self.generated_powerup
                    self.powerup_used = 1

    def on_message(self, client, userdata, message):
        print('Received message: "' + str(message.payload) + '" on topic "' +
        message.topic + '" with QoS ' + str(message.qos))
        packet = json.loads(message.payload)
        user = packet["username"]

        if "leader" in packet:
            self.next_leader = 1
            self.pose_leader = packet["leader"]
            if packet["leader"] == self.nickname: ## I am the leader 
                self.send_my_pose = 1
            else: ## ___ is the leader 
                self.pose_updated = 0 
                self.move_on = 0
                self.send_my_pose = 0 
        if "round_over" in packet: # creator sends this across when the round is over --> don't keep waiting for others now
            self.waiting_for_others = 0
            self.current_powerup = ''
            self.move_on = 1
            if self.pose_leader == self.nickname:
                self.level_score = packet["round_over"]
            if "pictures" in packet:
                self.display_pictures = 1
        if "gesture" in packet:
            print(packet["gesture"])
            self.on_gesture(packet["gesture"],user=user)
        if "send_my_pose" in packet and user != self.nickname:
            self.pose_updated = 1
            self.current_powerup = packet["send_my_pose"] 
            self.pose = packet["pose"]
            print(type(self.pose))
            print(packet["pose"])
            pass 
        if "scoreboard" in packet: 
            self.total_scores = packet["scoreboard"]
            self.score_received = 1
        if "score" in packet and self.creator == 1:
            score = packet["score"]
            self.round_scores[user] = score
            self.total_scores[user] += score
            if score > self.max_multi_score_round:
                self.max_multi_score_round = score 
                self.round_score_leader = user

            if len(self.round_scores) == self.num_users:
                ## round is over 
                self.round_num += 1
                self.move_on = 1
                total = 0 
                for key, value in self.round_scores.items():
                    total += value 
                total = int(15 - (total/self.num_users))
                if self.current_powerup == 'double_points':
                    total *= 2
                self.total_scores[self.pose_leader] += total 
                sorted_totals = {}
                sorted_keys = sorted(self.total_scores, key=self.total_scores.get, reverse=True)  # [1, 3, 2]

                for w in sorted_keys:
                    sorted_totals[w] = self.total_scores[w]

                if self.round_num >= self.num_users + 1:
                    packet = {
                        "username": self.nickname,
                        "round_over": total,
                        "scoreboard": sorted_totals,
                        "winner": self.round_score_leader,
                        "round_num": self.round_num,
                        "pictures": True
                    }
                    self.round_num = 0
                else:
                    packet = {
                        "username": self.nickname,
                        "round_over": total,
                        "scoreboard": sorted_totals,
                        "winner": self.round_score_leader,
                        "round_num": self.round_num
                    }
                self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                self.round_scores = {}
                self.max_multi_score_round = -1 
                self.round_score_leader = ''
        if "player_left" in packet:
            self.show_screen('', generic_txt='Someone left the game. Ending game now.')
            self.game()
        if "join" in packet and self.creator == 1:         
            f = open("room_info.csv", "a")
            f.write('{},{}\n'.format(user, 0))
            f.close()
            self.client_aws.upload_file('room_info.csv', self.room_name, "room_info.csv")
            self.num_users += 1
            self.users[self.num_users] = user
            self.total_scores[user] = 0
            send_joined_users = []
            for _, cur_user in self.users.items():
                send_joined_users.append(cur_user)
            packet = {
                "username": self.nickname,
                "lobby_users": send_joined_users
            }
            self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
        if "start_mult" in packet and self.creator == 0:
            self.multi_start = 1
            self.num_users = packet["start_mult"]
        if "winner" in packet:
            if self.creator == 0: 
                self.round_num = packet["round_num"]
            if packet["winner"] == self.nickname:
                pose = 'pose' + str(self.round_num) + '.jpg'
                self.client_aws.upload_file('pose.jpg', self.room_name, pose)
        if "lobby_users" in packet and self.creator == 0:
            self.lobby_users = packet["lobby_users"]

    def createaws(self):
        valid = 0
        try:
            self.bucket = self.client_aws.create_bucket(Bucket= self.room_name)
        except:
            self.show_screen('could_not_create')
            valid = 1
        if valid == 1:
            self.game()
        try:
            self.client_aws.head_object(Bucket=self.room_name, Key='do_not_join.txt')
            self.show_screen('',generic_txt='Room not available. Please try again.')
            self.game()
        except ClientError as e:
            try:
                self.client_aws.head_object(Bucket=self.room_name, Key='room_info.csv')
            except ClientError as e:
                self.creator = 1 
                self.users[self.num_users] = self.nickname
                self.total_scores[self.nickname] = 0
                self.client_mqtt.subscribe(self.room_name, qos=1)
                packet = {
                    "username": self.nickname
                }
                self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                print(self.room_name)
                f = open("room_info.csv", "w")
                f.write('{},{}\n'.format(self.nickname,self.user_score))
                f.close()
                self.client_aws.upload_file('room_info.csv', self.room_name, "room_info.csv")
                #local file name, bucket, remote file name
                return

            # you're the joiner 
            self.client_mqtt.subscribe(self.room_name, qos=1)
            print(self.room_name)
            packet = {
                "username": self.nickname,
                "join": True
            }
            self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)

    def change_diff(self, diff):
        print("Change difficulty " + diff)
        if diff == "easy":
            self.difficulty = 0
        elif diff == "medium":
            self.difficulty = 1
        elif diff == "hard":
            self.difficulty = 2
        print("difficulty: {}".format(self.difficulty))
    
    def change_mode(self, diff):
        print("Change mode " + diff)
        if diff == "single":
            self.mode = 0
        elif diff == "multi":
            self.mode = 1
        elif diff == "tutorial":
            self.mode = 2
        elif diff == "calibrate":
            self.mode = 3
        print("mode: {}".format(self.mode))

    def enter_sent(self, enter):
        print("enter voiced")
        self.enter_pressed = True

    def tutorial(self):
        ## tutorial
        print('hello')
        ## show rules first 
        self.mode = 2
        self.show_screen('tutorial')
    def show_pictures(self):
        pics = []
        for user in range(self.num_users+1):
            self.client_aws.download_file(self.room_name, 'pose'+ str(user+1) + '.jpg', 'pose'+ str(user+1) + '.jpg')
            pic = cv2.imread('pose'+ str(user+1) + '.jpg')
            pics.append(pic)
        if (self.num_users+1) % 2 == 1: # then concatenate first half + 1 vertically and next one vertically
            left = pics[0]
            add = np.zeros(shape=left.shape, dtype=np.uint8)
            for i in range(1, int(len(pics)/2)):
                left = np.concatenate((left, pics[i]), axis = 0)
            left = np.concatenate((left, add), axis = 0)
            right = pics[int(len(pics)/2)]
            for i in range(int(len(pics)/2) + 1, len(pics)):
                right = np.concatenate((right, pics[i]), axis = 0)
            full = np.concatenate((right,left), axis=1)
            cv2.imshow(WINDOWNAME,full)
        else:
            left = pics[0]
            for i in range(1, int(len(pics)/2)):
                left = np.concatenate((left, pics[i]), axis = 0)
            right = pics[int(len(pics)/2)]
            for i in range(int(len(pics)/2) + 1, len(pics)):
                right = np.concatenate((right, pics[i]), axis = 0)
            full = np.concatenate((left,right), axis=1)
            cv2.imshow(WINDOWNAME,full)
        cv2.waitKey(5000) 
        
    def show_screen(self, screen_type, points = 0, generic_txt = '', no_enter = 0):
        frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
        txt = ''
        if screen_type == 'start':
            words = ['HOLE ', 'IN ', 'THE ', 'WALL']
            for word in words:
                txt += word
                cv2.putText(frame, txt, (140, 180), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA) # 40 
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(500): 
                        break
            cv2.putText(frame, "Single Player Mode --- Enter", (175, 260), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Multi-Player Mode --- 1", (175, 310), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Tutorial --- 2", (175, 360), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Calibrate --- 3", (175, 410), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "-->",(135,260), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            
            while True:
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    if self.mode == -1:
                        self.mode = 0
                    break
                elif key == ZERO_KEY:
                    self.mode = 0
                elif key == ONE_KEY:
                    self.mode = 1
                elif key == TWO_KEY:
                    self.mode = 2
                elif key == THREE_KEY:
                    self.mode = 3
                
                if self.mode == 0:
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, txt, (140, 180), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Single Player Mode --- Enter", (175, 260), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Multi-Player Mode --- 1", (175, 310), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Tutorial --- 2", (175, 360), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Calibrate --- 3", (175, 410), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,260), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                elif self.mode == 1:
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, txt, (140, 180), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Single Player Mode --- 0", (175, 260), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Multi-Player Mode --- Enter", (175, 310), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Tutorial --- 2", (175, 360), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Calibrate --- 3", (175, 410), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,310), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                elif self.mode == 2:
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, txt, (140, 180), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Single Player Mode --- 0", (175, 260), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Multi-Player Mode --- 1", (175, 310), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Tutorial --- Enter", (175, 360), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Calibrate --- 3", (175, 410), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135, 360), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                elif self.mode == 3:
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, txt, (140, 180), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Single Player Mode --- 0", (175, 260), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Multi-Player Mode --- 1", (175, 310), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Tutorial --- 2", (175, 360), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Calibrate --- Enter", (175, 410), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135, 410), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                
        elif screen_type == 'difficulty':
            cv2.putText(frame, 'Select a difficulty:', (140, 220), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "-->",(135,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Easy --- Enter", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Medium --- \'m\'", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Hard --- \'h\'", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            self.difficulty = 0
            while True:
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    break
                elif key == ord('e'):
                    self.difficulty = 0
                elif key == ord('m'):
                    self.difficulty = 1
                elif key == ord('h'):
                    self.difficulty = 2

                if self.difficulty == 0:
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, 'Select a difficulty:', (140, 220), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Easy --- Enter", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Medium --- \'m\'", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Hard --- \'h\'", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                elif self.difficulty == 1:
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, 'Select a difficulty:', (140, 220), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Easy --- \'e\'", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Medium --- Enter", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Hard --- \'h\'", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                elif self.difficulty == 2:
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, 'Select a difficulty:', (140, 220), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Easy --- \'e\'", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Medium --- \'m\'", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Hard --- Enter", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)       
        elif screen_type == 'level':
            words = ['LEVEL ', '{}'.format(self.level_number)]        
            for word in words:
                txt += word
                cv2.putText(frame, txt, (140, 220), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(500): 
                        break
            cv2.putText(frame, "Press any key to start.", (140, 300), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key > 0 or self.enter_pressed == True:
                    self.enter_pressed = False
                    break
        elif screen_type == 'level_end':
            words = ['Level End']
            for word in words:
                txt += word
                cv2.putText(frame, txt, (140, 220), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(500): 
                        break
            if self.speed_up_used:
                cv2.putText(frame, "DOUBLE POINTS!!", (140, 300), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "This round: {} points".format(points), (140, 350), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Overall: {} points".format(self.user_score), (140, 400), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(4000)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                break
        elif screen_type == 'pause':
            cv2.putText(frame, 'Pause Screen', (140, 220), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Main Menu --- Enter", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Exit --- ESC Key", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Un-pause ---- Double Tap Gesture", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "-->",(135,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            if DEBUG == 3:
                return cv2.waitKey(0)
        elif screen_type == 'room':
            cv2.putText(frame, "Enter a 6-character room code:",(115,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            for i in range(len(self.room)):
                cv2.putText(frame, self.room[i], (145 + 20*i,240), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            num = 0

            while True:
                key = cv2.waitKey(0)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif num == len(self.room) and key == ENTER_KEY:
                    return # go to aws creation
                else:
                    if key == BACK_KEY:
                        if num > 0:
                            num -= 1
                        self.room[num] = '*'
                    elif num >= len(self.room):
                        continue
                    elif chr(key)!= '*':
                        self.room[num] = chr(key)
                        num += 1
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, "Enter a 6-character room code:",(115,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    for i in range(len(self.room)):
                        cv2.putText(frame, self.room[i], (145 + 20*i,240), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
        elif screen_type == 'nickname':
            cv2.putText(frame, "Nickname:",(115,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(0)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key == ENTER_KEY:
                    self.nickname = ''.join(self.nickname)
                    return 
                else:
                    if key == BACK_KEY:
                        if len(self.nickname) > 0:
                            self.nickname.pop()
                    else: 
                        self.nickname.append(chr(key))
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, "Nickname:",(115,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    for i in range(len(self.nickname)):
                        cv2.putText(frame, self.nickname[i], (145 + 20*i,240), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
            return
        elif screen_type == 'no_room':
            cv2.putText(frame, "Room {}".format(ROOM+''.join(self.room)),(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "does not exist. Please try again later.",(140,240), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(0)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key == ENTER_KEY:
                    self.multiplayer()
        elif screen_type == 'could_not_create':
            cv2.putText(frame, "Could not create room. Please try again.".format(ROOM+''.join(self.room)),(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(0)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key == ENTER_KEY:
                    self.multiplayer()
        elif screen_type == 'password':
            cv2.putText(frame, "Enter the room password:",(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            for i in range(len(self.room)):
                cv2.putText(frame, self.room[i], (130 + 20*i,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            num = 0
            while True:
                key = cv2.waitKey(0)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
          
                elif ''.join(self.password) == self.true_pass and key == ENTER_KEY:
                    return # password is correct
                else:
                    if key == BACK_KEY:
                        if len(self.password) > 0:
                            self.password.pop()
                    else: 
                        self.nickname.append(chr(key))    
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, "Enter the room password:",(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    for i in range(len(self.password)):
                        cv2.putText(frame, '*', (115 + 20*i,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
            return
        elif screen_type == 'start_game_multi':
            while True:
                frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                i = 0
                user_info = self.users.copy()
                for key, value in user_info.items():
                    cv2.putText(frame, "{} is in the lobby.".format(value),(200,240 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    i += 1
                cv2.putText(frame, "Press Enter to Start the Game.",(140,200), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.putText(frame, "You're in room \'{}\'.".format(''.join(self.room)),(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.imshow(WINDOWNAME, frame)
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                elif key == ENTER_KEY:
                    # send an update to everybody 
                    # game start 
                    if self.num_users < 1:
                        continue
                    packet = {
                        "username": self.nickname,
                        "start_mult": self.num_users
                    }
                    self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                    f = open("do_not_join.txt", "w")
                    f.write('do not join')
                    f.close()
                    self.client_aws.upload_file('do_not_join.txt', self.room_name, "do_not_join.txt")
                    return
        elif screen_type == 'waiting_for_creator':
            while True:
                frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                i = 0
                if len(self.lobby_users) > 0:
                    cv2.putText(frame, "Please wait for {} to start the game.".format(self.lobby_users[0]),(140,200), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "You're in room \'{}\'.".format(''.join(self.room)),(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    for cur_user in self.lobby_users:
                        cv2.putText(frame, "{} is in the lobby.".format(cur_user),(200,240 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                        i += 1
                else:
                    cv2.putText(frame, "Initializing...",(140,200), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                
                cv2.imshow(WINDOWNAME, frame)    
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if self.multi_start == 1:
                    return
                pass
        elif screen_type == 'waiting_for_new_pose':
            cv2.putText(frame, "Please wait, assigning new leader.",(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            start_time = time.perf_counter()
            while self.next_leader == 0: #while in this loop, we're waiting for pose leader 
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                
            self.next_leader = 0
            frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
            txt = ''
            cv2.putText(frame, "Please wait for {} to create a pose!".format(self.pose_leader),(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True: #while in this loop, we're waiting for pose leader 
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if self.pose_updated == 1: #local user tries to fit in the hole now
                    start_time = time.perf_counter()
                    user_vid_weight = 1
                    while True:
                        key = cv2.waitKey(1)
                        _, frame = self.cap.read()
                        if self.current_powerup != 'mirror':
                            frame = cv2.flip(frame, 1)
                        original = np.copy(frame)
                        time_elapsed = int(time.perf_counter() - start_time)
                        time_remaining = 10 - time_elapsed
                        contour_weight = 1
                        contour, _ = self.PoseEstimator.getContourFromPoints(self.pose, self.height, self.width)
                        contour = cv2.bitwise_not(contour)
                        if self.current_powerup == 'mirror':
                            contour = cv2.flip(contour,1)
                        if self.current_powerup == 'lights_out':
                            user_vid_weight = (10 - time_elapsed)/10
                            if user_vid_weight <= 0:
                                user_vid_weight = 0
                            frame = cv2.addWeighted(frame, user_vid_weight, contour,contour_weight,0) # @NOTE make gradient
                        else:
                            frame = cv2.addWeighted(frame,self.uservid_weight,contour,contour_weight,0)
                        if time_remaining <= -1:
                            cv2.putText(frame, "Time Remaining: {}".format(0), (10, 50), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                        else:
                            cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                        if self.current_powerup != '':
                            cv2.putText(frame, "{} used the {} powerup on you!".format(self.pose_leader,self.current_powerup), (10, 450), FONT, FONTSCALE - 0.25, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)

                        cv2.imshow(WINDOWNAME, frame)
                        if time_remaining <= -1: 
                            time_remaining = 0
                            original, points = self.PoseEstimator.getSkeleton(original)
                            self.level_score = self.PoseDetector.isWithinContour(points, contour, self.height, self.width)
                            for pair in self.PoseEstimator.POSE_PAIRS:
                                point1 = points[pair[0]]
                                point2 = points[pair[1]]

                                if point1 and point2:
                                    cv2.line(frame, tuple(point1), tuple(point2), self.PoseEstimator.SKELETON_LINECOLOR, 2)
                                    cv2.circle(frame, tuple(point1), 8, self.PoseEstimator.SKELETON_POINTCOLOR, thickness=-1, lineType=cv2.FILLED)
                            cv2.imshow(WINDOWNAME, frame)
                            cv2.imwrite('pose.jpg',frame)
                            key = cv2.waitKey(2000)
                            packet = {
                                "username": self.nickname,
                                "score": self.level_score
                            }
                            self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                            self.pose_updated = 0
                            break
                    return
                if self.send_my_pose == 1:
                    self.send_pose()
                    self.waiting_for_others = 1
                    self.show_screen('waiting_for_others_pose')
                    return
                if self.move_on == 1 and self.creator == 1:
                    return
                pass    
        elif screen_type == 'level_end_multi':
            cv2.putText(frame,'Your score is {}'.format(self.level_score), (140, 220), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            start_time = time.perf_counter()
            while True:
                if self.creator == 1:
                    time_elapsed = int(time.perf_counter() - start_time)
                    time_remaining = 60 - time_elapsed
                    if time_remaining <= -1: 
                        packet = {
                            "username": self.nickname,
                            "player_left": 1
                        }
                        self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if self.score_received == 1:
                    time.sleep(2)
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame,'Scoreboard:'.format(self.level_score), (120, 120), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    i = 0 
                    for key, value in self.total_scores.items():
                        cv2.putText(frame,'{}: {}'.format(key, value), (120, 140 + 20*i), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                        i += 1 
                    cv2.imshow(WINDOWNAME, frame)
                    cv2.waitKey(2000)
                    self.score_received = 0
                    if self.display_pictures == 1:
                        self.show_pictures()
                        self.display_pictures = 0
                    return
                    # if self.move_on == 1 and self.creator == 1:
                    #     return
        elif screen_type == 'waiting_for_others_pose':
            self.next_leader = 0
            cv2.putText(frame, "Waiting for other users to match your pose",(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            if self.powerup_used == 1:
                cv2.putText(frame, "{} powerup used!".format(self.current_powerup),(140,240), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.putText(frame, "{}".format(self.current_description),(140,260), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            start_time = time.perf_counter()
            while True: #while in this loop, we're waiting for pose leader 
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if self.waiting_for_others == 0: #we're no longer waiting --> signify end of turn
                    return
                if self.creator == 1 and self.waiting_for_others == 1:
                    time_elapsed = int(time.perf_counter() - start_time)
                    time_remaining = 60 - time_elapsed
                    if time_remaining <= -1: 
                        packet = {
                            "username": self.nickname,
                            "player_left": 1
                        }
                        self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                pass    
        elif screen_type == 'tutorial':
            phrases = ["Welcome to Hole in the Wall!",
            "To play, you'll need:", 
            "   - a laptop with front facing camera & microphone", 
            "   - Raspberry Pi & IMU", "   - Internet connection", 
            "...and you're ready to go!",
            "",
            "",
            "Press 0 to view Single Player Rules", 
            "Press 1 to view Mutltiplayer Rules"]
            i = 0
            for phrase in phrases:
                cv2.putText(frame, phrase,(100, 140 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                i += 1
            cv2.imshow(WINDOWNAME, frame)
            while True:  
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                # @TODO: make 0 or 1 instead of enter 
                if key == ZERO_KEY: # or self.enter_pressed == True: 
                    # self.enter_pressed = False
                    self.show_screen('singletutorial')
                elif key == ONE_KEY: # or self.enter_pressed == True:
                    # self.enter_pressed = False
                    self.show_screen('multitutorial')
        elif screen_type == 'singletutorial':
            phrases = ["Single Player Rules:",
            "- Timer in the top left corner indicates time remaining.", 
            "- The screen shows the hole you must fit your body in.", 
            "- Fit your body in the hole before the clock hits ZERO!",
            "- The better you fit, the higher your score.",
            "",
            "",
            "",
            "Press Enter to go to the Power Ups page"]
            i = 0
            for phrase in phrases:
                cv2.putText(frame, phrase,(100, 140 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                i += 1
            cv2.imshow(WINDOWNAME, frame)
            while True:  
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    self.show_screen('singletutorial2')
        elif screen_type == 'singletutorial2':
            phrases = ["Single Player Powerups:",
            "- Extend the Deadline: doubles the timer", 
            "- Double Points: ends the round and gives you double points",
            "                  for your pose.",
            "",
            "",
            "",
            "",
            "Press Enter to go to back to the Main Menu"] 
            i = 0
            for phrase in phrases:
                cv2.putText(frame, phrase,(100, 140 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                i += 1
            cv2.imshow(WINDOWNAME, frame)
            while True: 
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    self.game()
        elif screen_type == 'multitutorial':
            phrases = ["Multi-Player Rules:",
            "- Pose Leader has 10 secs to create the hole in the wall.",
            "- Other players have 10 secs to fit within the created hole.",
            "- Timer in the top left corner indicates time remaining.", 
            "- The screen shows the hole you must fit your body in.", 
            "- Fit your body in the hole before the clock hits ZERO!",
            "- The better you fit, the higher your score.",
            "",
            "Press Enter to go to the Power Ups page"]
            i = 0
            for phrase in phrases:
                cv2.putText(frame, phrase,(100, 140 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                i += 1
            cv2.imshow(WINDOWNAME, frame)
            while True:  
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    self.show_screen('multitutorial2')
        elif screen_type == 'multitutorial2':
            phrases = ["Multi-Player Powerups:",
            "- Mirror the Wall: mirrors your opponent(s) walls",
            "- Lights Out: blacks out your opponent(s) screen", 
            "- Double Points: gives you double points for your pose",
            "",
            "",
            "",
            "",
            "Press Enter to go to back to the Main Menu"] 
            i = 0
            for phrase in phrases:
                cv2.putText(frame, phrase,(100, 140 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                i += 1
            cv2.imshow(WINDOWNAME, frame)
            while True: 
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    self.game()
        elif screen_type == 'calibrate':
            phrases = ["Calibration:",
            "Now, we will help you calibrate your camera.", 
            "",
            "Please tilt your camera or stand further away to fit",
            "within the test contour!",
            "",
            "",
            "Press Enter to start calibrating"]

            i = 0
            for phrase in phrases:
                cv2.putText(frame, phrase,(100, 140 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                i += 1
            cv2.imshow(WINDOWNAME, frame)
            while True: 
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    return
        elif generic_txt != '':
            cv2.putText(frame, "{}".format(generic_txt),(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True: #while in this loop, we're waiting for pose leader 
                if no_enter == 1: 
                    return    
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if key == ENTER_KEY:
                    return
                pass    
    def calibrate(self):
        ## calibrate
        print('hello again')
        ## show rules first 
        self.mode = 3
        self.show_screen('calibrate')
        contour = cv2.imread(os.path.join(POSES, 'test.jpg'))
        contour = cv2.bitwise_not(contour)
        valid_config = 0
        while valid_config == 0:
            start_time = int(time.perf_counter())
            while True:
                time_elapsed = int(time.perf_counter()-start_time)
                time_remaining = 10 - time_elapsed
                key = cv2.waitKey(1)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                _, frame = self.cap.read()
                frame = cv2.flip(frame, 1)
                original = np.copy(frame)
                frame = cv2.addWeighted(frame,self.uservid_weight,contour,1,0)
                if time_remaining <= -1:
                    cv2.putText(frame, "Time Remaining: {}".format(0), (10, 50), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                else:
                    cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.putText(frame, "Step in the Contour.", (375, 50), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.imshow(WINDOWNAME, frame)
                if time_remaining <= -1:
                    ## check their pose 
                    cv2.imshow(WINDOWNAME, frame)
                    frame, points = self.PoseEstimator.getSkeleton(original)
                    level_score = self.PoseDetector.isWithinContour(points, contour)
                    cv2.imshow(WINDOWNAME,frame)
                    cv2.waitKey(2000)
                    if level_score >= 8:
                        self.show_screen('',generic_txt='Calibration complete! Have fun!', no_enter = 1)
                        valid_config = 1
                    else:
                        self.show_screen('',generic_txt='Calibration failed! Please try again.', no_enter = 1)
                    cv2.waitKey(2000)
                    break
        ## return to main menu 
        self.game() 

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
            cv2.putText(frame, '{} x'.format(powerup_num_left), (640-110, 480-row_bias-20), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            num+=1
        
        cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
        cv2.putText(frame, "Score: {}".format(self.user_score), (500, 50), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
        return frame, time_remaining, original
    
    old_contour_num = 0
    def level(self):
        self.play = True
        timer_old = self.TIMER_THRESHOLD
        
        while True:
            if self.difficulty == 0:
                contour_num = random.randint(0,len(easy_contours)-1)
                contour = easy_contours[contour_num]
            elif self.difficulty == 1:
                contour_num = random.randint(0,len(medium_contours)-1)
                contour = medium_contours[contour_num]
            elif self.difficulty == 2:
                contour_num = random.randint(0,len(hard_contours)-1)
                contour = hard_contours[contour_num]
            if contour_num != self.old_contour_num:
                self.old_contour_num = contour_num
                break
        
        contour = cv2.flip(contour,1)
        frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
        self.show_screen('level')
        start_time = time.perf_counter()
        override_time = False
        stop = False
        while True:
            key = cv2.waitKey(1)
            if key == ESC_KEY:
                self.__del__()
                exit(0)
            elif key == ord('s') or self.speed_up_used == True:
                override_time = True
            if self.play == False:
                if key == ENTER_KEY:
                    self.game()
                self.show_screen('pause')
                pass
                continue
            if DEBUG == 3:
                if key == ord('p'):
                    if self.play:
                        self.play = False
                        self.reset_timer = time.perf_counter()
                        pass
                    while self.play == False:
                        new_key = self.show_screen('pause')
                        if new_key == ord('p'):
                            self.TIMER_THRESHOLD += int(time.perf_counter() - self.reset_timer)
                            self.reset_timer = -1
                            self.play = True
                        elif new_key == ESC_KEY:
                            self.__del__()
                            exit(0)
                        elif new_key == ENTER_KEY:
                            self.game()
            else: # use only gesture code 
                pass
            if self.slow_down_used == True:
                self.TIMER_THRESHOLD *= 2
                self.slow_down_used = False
            
            _, frame = self.cap.read()
            frame = cv2.flip(frame,1)
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
                    cv2.imshow(WINDOWNAME, original)
                    while True:
                        if cv2.waitKey(0):
                            break
                if self.speed_up_used:
                    level_score *= 2
                self.user_score += level_score
                self.show_screen('level_end',points=level_score)
                return
            pass

    def singleplayer(self):
        while self.difficulty == -1:
            self.show_screen('difficulty')
        self.client_mqtt.subscribe(ROOM, qos=1)
        if raspi: 
            x = threading.Thread(target = self.remote_connection.run, daemon=True)
            x.start()
        while True:
            self.level_number += 1
            self.slow_down_used = False
            self.speed_up_used = False
            self.play = False
            self.level()
            if self.TIMER_THRESHOLD > 5:
                self.TIMER_THRESHOLD -= 2
    def send_pose(self):
        global rand_int
        self.powerup_used = 0 # set this when powerup is used
        self.move_on = 0
        start_time = time.perf_counter()
        pose_num = random.randint(0,2)
        gesture_name = self.multi_gesture_names[pose_num]
        self.generated_powerup = self.multi_powerups[pose_num]
        self.current_description = self.multi_description[pose_num]
        while self.send_my_pose == 1: 
            key = cv2.waitKey(1)
            _, frame = self.cap.read()
            frame = cv2.flip(frame, 1)
            time_elapsed = int(time.perf_counter() - start_time)
            time_remaining = 10 - time_elapsed
            if time_remaining <= -1:
                cv2.putText(frame, "Time Remaining: {}".format(0), (10, 50), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            else:
                cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Strike a pose!".format(time_remaining), (375, 50), FONT, FONTSCALE, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            if self.current_powerup != self.generated_powerup:
                cv2.putText(frame, "Do the {} gesture to get the {} powerup!".format(gesture_name,self.generated_powerup), (10, 450), FONT, FONTSCALE - 0.25, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            else: 
                cv2.putText(frame, "You gained the {} powerup!".format(self.generated_powerup), (10, 450), FONT, FONTSCALE - 0.25, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            if time_remaining <= -1: 
                time_remaining = 0
                frame, points = self.PoseEstimator.getSkeleton(frame)
                for pair in self.PoseEstimator.POSE_PAIRS:
                    point1 = points[pair[0]]
                    point2 = points[pair[1]]
                    if point1 and point2:
                        cv2.line(frame, tuple(point1), tuple(point2), self.PoseEstimator.SKELETON_LINECOLOR, 2)
                        cv2.circle(frame, tuple(point1), 8, self.PoseEstimator.SKELETON_POINTCOLOR, thickness=-1, lineType=cv2.FILLED)
                cv2.imshow(WINDOWNAME, frame)
                cv2.waitKey(2000)
                self.send_my_pose = 0
                packet = {
                    "username": self.nickname,
                    "send_my_pose": self.current_powerup,
                    "pose": points
                }
                self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                return
        pass 
    def creator_code(self):
        self.show_screen('start_game_multi') 
        # time.sleep(3)
        cur_user = 0
        while True:
            ## send message to person whose turn it is 
            if self.move_on == 0: #and self.users[cur_user] != self.nickname:
                self.show_screen('waiting_for_new_pose')
                self.show_screen('level_end_multi')
            
            elif self.move_on == 1:
                if self.users[cur_user] == self.nickname:
                    print('it\'s {}\'s turn'.format(self.users[cur_user]))
                    packet = {
                        "username": self.nickname,
                        "leader": self.users[cur_user]
                    }
                    self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                    self.send_my_pose = 1
                    self.send_pose()
                    self.waiting_for_others = 1
                    self.show_screen('waiting_for_others_pose')
                    self.show_screen('level_end_multi')
                else:
                    packet = {
                        "username": self.nickname,
                        "leader": self.users[cur_user]
                    }
                    print('it\'s {}\'s turn'.format(self.users[cur_user]))
                    self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                    self.move_on = 0
            
                cur_user += 1
                cur_user %= (self.num_users+1)
    def joiner_code(self):
        self.show_screen('waiting_for_creator')
        while True:
            self.show_screen('waiting_for_new_pose')
            self.show_screen('level_end_multi')
            
    def multiplayer(self):
        self.show_screen('room')
        self.show_screen('nickname') 
        self.room_name = ROOM + ''.join(self.room)
        print(self.room_name)
        self.createaws()
        if raspi: 
            self.remote_connection.set_conn_info('m', self.nickname, ''.join(self.room))
            x = threading.Thread(target = self.remote_connection.run, daemon=True)
            x.start()
        if self.creator == 1:
            self.creator_code()
        else: # regular user 
            self.joiner_code()

    def game(self):
        self.user_score = 0
        self.level_number = 0
        self.uservid_weight = 1
        self.mode = -1 # 0 for single player, 1 for multi player
        self.difficulty = -1 # 0 for easy, 1 for medium, 2 for hard
        self.TIMER_THRESHOLD = 20
        self.play = False
        self.reset_timer = -1
        self.show_screen('start')
        self.nickname = []
        self.password = []
        self.room = ['*','*','*','*','*','*']
        if self.mode == 0:
            self.singleplayer()
        elif self.mode == 1: 
            self.multiplayer()
        elif self.mode == 2:
            self.tutorial()
        elif self.mode == 3:
            self.calibrate()
        else:
            print('error')
            exit(1)

    def __del__(self):
        if self.mode == 1 and self.room_name != '' and len(self.nickname) > 0 and self.creator == 1:
            try: 
                s3 = boto3.resource(
                    's3',
                    aws_access_key_id=ACCESS_KEY,
                    aws_secret_access_key=SECRET_KEY
                )
                bucket = s3.Bucket(self.room_name)
                for key in bucket.objects.all():
                    key.delete()
                bucket.delete()
            except:
                print('deleting')
        packet = {
            "username": 'cancel',
            "disconnect": 'please'
        }
        if raspi: 
            self.client_mqtt.publish(ROOM, json.dumps(packet), qos=1)
        else: 
            self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
        self.cap.release() 
        cv2.destroyAllWindows()
        self.client_mqtt.loop_stop()
        self.client_mqtt.disconnect() 
        
def main():
    game = Game()
    game.game()

if __name__ == '__main__':
    main()