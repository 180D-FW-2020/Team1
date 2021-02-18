"""
game.py: file to run the program
overall handler for the output to user
@TODO: 
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
import paho.mqtt.client as mqtt
import json
import boto3
from botocore.config import Config
from botocore.client import ClientError
import threading
import key

# NOTE move power up/gesture txt down for multiplayer
region='us-east-1'
ROOM = 'ece180d-team1-room-'

FONTCOLORWHITE = (255,255,255)
FONTCOLORBLACK = (0,0,0)
FONTCOLORDEFAULT = (236, 183, 76) ## blue
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONTSIZE = 1

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

# mfile.write("Hello World!")
# mfile.close()

connection_string = "ece180d/team1"

# 1 to see all the contours, 2 to see the points after contour detection, 3 for testing the pause button
DEBUG = 0

# KEY Definitions
ENTER_KEY = 13
ESC_KEY = 27
UP_KEY = 38
DOWN_KEY = 40
ZERO_KEY = 48
ONE_KEY = 49
TWO_KEY = 50
BACK_KEY = 8

STATE_WAITING_FOR_CREATOR = 0
STATE_WAITING_FOR_POSE_RECEIPT = 1
STATE_GOT_POSE = 2
STATE_MY_TURN = 3

TIMER_THRESHOLD_SMALL = 5


# WINDOW Definition 
WINDOWNAME = 'Hole in the Wall!'
cv2.namedWindow(WINDOWNAME, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(WINDOWNAME,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

# FILESYSTEM Definitions 
GRAPHICS = '.\graphics\\'
POSES = 'poses\\'
POWERUPS = 'powerups\\'
PATH = GRAPHICS + POSES
DIFFICULTIES = ['easy\\', 'medium\\', 'hard\\']

# FILESYSTEM Work 
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
        self.multi_start = 0 #should we start or no (creator tells the rest)

        # User variables
        self.user_score = 0
        self.level_number = 0
        self.uservid_weight = 1
        self.mode = -1 # 0 for single player, 1 for multi player
        self.enter_pressed = False
        self.difficulty = -1 # 0 for easy, 1 for medium, 2 for hard
        self.TIMER_THRESHOLD = 20
        self.play = False
        self.reset_timer = -1

        # multi user variables
        self.send_my_pose = 0 #1 means I'm the pose leader --> local user makes a pose
        self.move_on = 1 #1 means round is over, creator chooses next pose leader --> CREATOR only 
        self.pose_updated = 0 #1 means pose leader sent pose over mqtt --> ALL users should fit in hole 
        self.waiting_for_others = 0 #1 means that we (local user is pose leader) have sent our pose across and are waiting for others to finish fitting inside the hole 
        self.pose = [] # the pose we received from the pose leader 
        self.next_leader = 0 #1 means next leader has been chosen, move on to pose stuff
        self.level_score = 0
        # self.my_state
        self.score_received = 0
        self.pose_leader = ''
        self.round_scores = {} # creator keeps track of who got what score that specific round -- emptied after each round ends 
        self.total_scores = {} # creator keeps track of who has what score ovreal -- never empties 
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
        # @NOTE indexing should be same for round_scores and total_scores
    # start mqtt 
    def on_connect(self, client, userdata, flags, rc):
        print("Connection returned result: "+str(rc))
        
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print('Unexpected Disconnect')
        else:
            print('Expected Disconnect')

    def on_gesture(self,gesture):
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
        # print(packet["username"])
        user = packet["username"]

        if "leader" in packet:
            self.next_leader = 1
            self.pose_leader = packet["leader"]
            if packet["leader"] == ''.join(self.nickname): ## I am the leader 
                self.send_my_pose = 1
            else: ## ___ is the leader 
                self.pose_updated = 0 
                self.move_on = 0
                self.send_my_pose = 0 
        if "round_over" in packet: # creator sends this across when the round is over --> don't keep waiting for others now
            self.waiting_for_others = 0
            self.current_powerup = ''
            self.move_on = 1
            if self.pose_leader == ''.join(self.nickname):
                self.level_score = packet["round_over"]
        if "gesture" in packet:
            print(packet["gesture"])
            self.on_gesture(packet["gesture"])
        if "send_my_pose" in packet and user != ''.join(self.nickname):
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
            # print(packet["score"])
            # indicate next round
            self.round_scores[user] = packet["score"]
            self.total_scores[user] += packet["score"]
            if len(self.round_scores) == self.num_users:
                ## round is over 
                self.move_on = 1
                total = 0 
                for key, value in self.round_scores.items():
                    total += value 
                total = int(15 - (total/self.num_users))
                if self.current_powerup == 'double_points':
                    total *= 2
                self.total_scores[self.pose_leader] += total 
                """
                implement csv logic here
                """
                packet = {
                    "username": ''.join(self.nickname),
                    "round_over": total,
                    "scoreboard": self.total_scores
                }
                self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                self.round_scores = {}
        if "player_left" in packet:
            self.show_screen('', generic_txt='Someone left the game. Ending game now.')
            self.game()
        if "join" in packet and self.creator == 1: # assuming initial message sends score
            # implement some stuff creator has to do when new players join via mqtt 
            # print(packet["join"])
            if packet["join"] == True:
                # joining 
                # if self.num_users == 4:
                #     pass # don't let them join, implement later 
                f = open("room_info.csv", "a")
                f.write('{},{}\n'.format(user, 0))
                f.close()
                self.client_aws.upload_file('room_info.csv', self.room_name, "room_info.csv")
                self.num_users += 1
                self.users[self.num_users] = user
                self.total_scores[user] = 0
            pass 
        if "start_mult" in packet and self.creator == 0:
            self.multi_start = 1
        
    # end mqtt
    def createaws(self):
        valid = 0
        try:
            self.bucket = self.client_aws.create_bucket(Bucket= self.room_name)
            # print(self.bucket)
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
            #print('does not exist') ## you're the creator 
            try:
                self.client_aws.head_object(Bucket=self.room_name, Key='room_info.csv')
            except ClientError as e:
                self.creator = 1 
                self.users[self.num_users] = ''.join(self.nickname)
                self.total_scores[''.join(self.nickname)] = 0
                self.client_mqtt.subscribe(self.room_name, qos=1)
                packet = {
                    "username": ''.join(self.nickname)
                }
                self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                print(self.room_name)
                f = open("room_info.csv", "w")
                f.write('{},{}\n'.format(''.join(self.nickname),self.user_score))
                f.close()
                self.client_aws.upload_file('room_info.csv', self.room_name, "room_info.csv")
                #local file name, bucket, remote file name
                return

            # you're the joiner 
            self.client_mqtt.subscribe(self.room_name, qos=1)
            print(self.room_name)
            packet = {
                "username": ''.join(self.nickname),
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
        print("mode: {}".format(self.mode))

    
    def enter_sent(self, enter):
        print("enter voiced")
        self.enter_pressed = True

    def tutorial(self):
        ## tutorial
        print('hello')
        ## show rules first 
        self.mode = 0
        self.show_screen('tutorial')
        
    def show_screen(self, screen_type, points = 0, generic_txt = '', no_enter = 0):
        frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
        txt = ''
        if screen_type == 'start':
            words = ['HOLE ', 'IN ', 'THE ', 'WALL']
            for word in words:
                txt += word
                cv2.putText(frame, txt, (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(500): 
                        break
            cv2.putText(frame, "Single Player Mode --- Enter", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Multi-Player Mode --- 1", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Tutorial --- 2", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "-->",(135,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
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
                elif key == ZERO_KEY or self.mode == 0:
                    if self.mode!= 0:
                        self.mode = 0
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, txt, (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Single Player Mode --- Enter", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Multi-Player Mode --- 1", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Tutorial --- 2", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                elif key == ONE_KEY or self.mode == 1:
                    if self.mode!= 1:
                        self.mode = 1
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, txt, (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Single Player Mode --- 0", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Multi-Player Mode --- Enter", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Tutorial --- 2", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                elif key == TWO_KEY or self.mode == 2:
                    if self.mode!= 2:
                        self.mode = 2
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, txt, (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Single Player Mode --- 0", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Multi-Player Mode --- 1", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Tutorial --- Enter", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                
        elif screen_type == 'difficulty':
            cv2.putText(frame, 'Select a difficulty:', (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
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
                    cv2.putText(frame, 'Select a difficulty:', (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Easy --- Enter", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Medium --- \'m\'", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Hard --- \'h\'", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                elif self.difficulty == 1:
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, 'Select a difficulty:', (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Easy --- \'e\'", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Medium --- Enter", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Hard --- \'h\'", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
                elif self.difficulty == 2:
                    frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                    cv2.putText(frame, 'Select a difficulty:', (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "-->",(135,400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Easy --- \'e\'", (175, 300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Medium --- \'m\'", (175, 350), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.putText(frame, "Hard --- Enter", (175, 400), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)       
        elif screen_type == 'level':
            words = ['LEVEL ', '{}'.format(self.level_number)]        
            for word in words:
                txt += word
                cv2.putText(frame, txt, (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(500): 
                        break
            cv2.putText(frame, "Press any key to start.", (140, 300), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
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
                cv2.putText(frame, txt, (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.imshow(WINDOWNAME, frame)
                while True:
                    if cv2.waitKey(500): 
                        break
            if self.speed_up_used:
                cv2.putText(frame, "DOUBLE POINTS!!", (140, 300), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "This round: {} points".format(points), (140, 350), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Overall: {} points".format(self.user_score), (140, 400), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                key = cv2.waitKey(4000)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                break
        elif screen_type == 'pause':
            cv2.putText(frame, 'Pause Screen', (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
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
                cv2.putText(frame, self.room[i], (115+ 20*i,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
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
                        cv2.putText(frame, self.room[i], (115+ 20*i,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
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
                        cv2.putText(frame, self.nickname[i], (115+ 20*i,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
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
                cv2.putText(frame, self.room[i], (130+ 20*i,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
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
                        cv2.putText(frame, '*', (115+ 20*i,300), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    cv2.imshow(WINDOWNAME, frame)
            return
        elif screen_type == 'start_game_multi':
            cv2.putText(frame, "Press Enter to Start the Game".format(ROOM+''.join(self.room)),(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
                frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
                i = 0
                for key, value in self.users.items():
                    cv2.putText(frame, "{} is in the lobby.".format(value),(200,240+i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    i += 1
                cv2.putText(frame, "Press Enter to Start the Game".format(ROOM+''.join(self.room)),(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
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
                        "username": ''.join(self.nickname),
                        "start_mult": True
                    }
                    self.client_mqtt.publish(self.room_name, json.dumps(packet), qos=1)
                    f = open("do_not_join.txt", "w")
                    f.write('do not join')
                    f.close()
                    self.client_aws.upload_file('do_not_join.txt', self.room_name, "do_not_join.txt")
                    return
        elif screen_type == 'waiting_for_creator':
            cv2.putText(frame, "Please wait for creator to start the game".format(ROOM+''.join(self.room)),(140,220), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            while True:
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
                    while True:
                        key = cv2.waitKey(1)
                        _, frame = self.cap.read()
                        if self.current_powerup != 'mirror':
                            frame = cv2.flip(frame, 1)
                        original = np.copy(frame)
                        time_elapsed = int(time.perf_counter() - start_time)
                        time_remaining = 10 - time_elapsed
                        contour_weight = 1
                        contour, _ = self.PoseEstimator.getContourFromPoints(self.pose)
                        contour = cv2.bitwise_not(contour)
                        if self.current_powerup == 'mirror':
                            contour = cv2.flip(contour,1)
                        if self.current_powerup == 'lights_out':
                            frame = cv2.addWeighted(frame, .2, contour,contour_weight,0) # @NOTE make gradient
                        else:
                            frame = cv2.addWeighted(frame,self.uservid_weight,contour,contour_weight,0)
                        cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                        # cv2.putText(frame, "Score: {}".format(self.user_score), (500, 50), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                        cv2.imshow(WINDOWNAME, frame)
                        if time_remaining <= -1: 
                            time_remaining = 0
                            original, points = self.PoseEstimator.getSkeleton(original)
                            self.level_score = self.PoseDetector.isWithinContour(points, contour)
                            for pair in self.PoseEstimator.POSE_PAIRS:
                                point1 = points[pair[0]]
                                point2 = points[pair[1]]

                                if point1 and point2:
                                    cv2.line(frame, tuple(point1), tuple(point2), (0, 255, 255), 2)
                                    cv2.circle(frame, tuple(point1), 8, (0, 0, 255), thickness=-1, lineType=cv2.FILLED)
                            cv2.imshow(WINDOWNAME, frame)
                            key = cv2.waitKey(2000)
                            packet = {
                                "username": ''.join(self.nickname),
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
            cv2.putText(frame,'Your score is {}'.format(self.level_score), (140, 220), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            start_time = time.perf_counter()
            while True:
                if self.creator == 1:
                    time_elapsed = int(time.perf_counter() - start_time)
                    time_remaining = 60 - time_elapsed
                    if time_remaining <= -1: 
                        packet = {
                            "username": ''.join(self.nickname),
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
                    cv2.putText(frame,'Scoreboard:'.format(self.level_score), (120, 120), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                    i = 0 
                    for key, value in self.total_scores.items():
                        cv2.putText(frame,'{}: {}'.format(key, value), (120, 140 + 20*i), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                        i += 1 
                    cv2.imshow(WINDOWNAME, frame)
                    cv2.waitKey(2000)
                    self.score_received = 0
                    return
                if self.move_on == 1 and self.creator == 1:
                    return
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
                            "username": ''.join(self.nickname),
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
            "Press Enter to go to the Rules page"]
            i = 0
            for phrase in phrases:
                cv2.putText(frame, phrase,(100, 140 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                i += 1
            cv2.imshow(WINDOWNAME, frame)
            while True: #while in this loop, we're waiting for pose leader 
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    self.show_screen('tutorial2')
        elif screen_type == 'tutorial2':
            phrases = ["Rules:",
            "- Timer in the top left corner indicates time remaining.", 
            "- The screen shows the hole you must fit your body in.", 
            "- Fit your body in the hole before the clock hits ZERO!",
            "- The better you fit, the higher your score.",
            "",
            "",
            "Press Enter to go to the Power Ups page"]
            i = 0
            for phrase in phrases:
                cv2.putText(frame, phrase,(100, 140 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                i += 1
            cv2.imshow(WINDOWNAME, frame)
            while True: #while in this loop, we're waiting for pose leader 
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    self.show_screen('tutorial3')
        elif screen_type == 'tutorial3':
            phrases = ["Powerups:",
            "- Extend the Deadline: doubles the timer", 
            "- Double Points: ends the round and gives you double points",
            "                  for your pose.",
            "",
            "",
            "Press Enter to go to the Calibration page"]#, 
            #"- Mirror the Wall: mirror’s your opponent(s) walls",
            #"- Lights Out: blacks out your opponent(s) screen"]

            i = 0
            for phrase in phrases:
                cv2.putText(frame, phrase,(100, 140 + i*25), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                i += 1
            cv2.imshow(WINDOWNAME, frame)
            while True: #while in this loop, we're waiting for pose leader 
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    self.show_screen('tutorial4')
        elif screen_type == 'tutorial4':
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
            while True: #while in this loop, we're waiting for pose leader 
                key = cv2.waitKey(10)
                if key == ESC_KEY:
                    self.__del__()
                    exit(0)
                if key == ENTER_KEY or self.enter_pressed == True:
                    self.enter_pressed = False
                    #self.show_screen('tutorial4')
                    self.calibrate()
                    self.game() 
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
        contour = cv2.imread(PATH + 'test.jpg')
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
                cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
                cv2.putText(frame, "Step in the Contour.", (375, 50), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
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
            cv2.putText(frame, '{} x'.format(powerup_num_left), (640-110, 480-row_bias-20), FONT, .5, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            num+=1
        
        cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
        cv2.putText(frame, "Score: {}".format(self.user_score), (500, 50), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
        # print('time remaining', time_remaining)
        return frame, time_remaining, original
    
    def level(self):
        self.play = True
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
        # print(start_time)
        override_time=False
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
                # print('original shape', original.shape)
                # print(contour.shape)
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
        ## include screen to say "you're up"
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
            # frame, time_remaining, original = self.editFrame(frame, start_time, contour, override_time=override_time)
            
            time_elapsed = int(time.perf_counter() - start_time)
            time_remaining = 10 - time_elapsed
            cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Strike a pose!".format(time_remaining), (375, 50), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.putText(frame, "Do the {} gesture to get the {} powerup!".format(gesture_name,self.generated_powerup), (10, 350), FONT, .8, FONTCOLORDEFAULT, FONTSIZE, lineType=cv2.LINE_AA)
            cv2.imshow(WINDOWNAME, frame)
            if time_remaining <= -1: 
                time_remaining = 0
                frame, points = self.PoseEstimator.getSkeleton(frame)
                for pair in self.PoseEstimator.POSE_PAIRS:
                    point1 = points[pair[0]]
                    point2 = points[pair[1]]
                    if point1 and point2:
                        cv2.line(frame, tuple(point1), tuple(point2), (0, 255, 255), 2)
                        cv2.circle(frame, tuple(point1), 8, (0, 0, 255), thickness=-1, lineType=cv2.FILLED)
                cv2.imshow(WINDOWNAME, frame)
                cv2.waitKey(2000)
                self.send_my_pose = 0
                packet = {
                    "username": ''.join(self.nickname),
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
            if self.move_on == 0: #and self.users[cur_user] != ''.join(self.nickname):
                self.show_screen('waiting_for_new_pose')
                self.show_screen('level_end_multi')
            
            elif self.move_on == 1:
                if self.users[cur_user] == ''.join(self.nickname):
                    print('it\'s {}\'s turn'.format(self.users[cur_user]))
                    packet = {
                        "username": ''.join(self.nickname),
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
                        "username": ''.join(self.nickname),
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
            # we got a new pose 
            # for i in range(len(self.pose)):
            #     self.pose[i] = tuple(self.pose[i])
            # _, _ = self.PoseEstimator.getContourFromPoints(self.pose)
            # contour = cv2.imread('Output-Contour.jpg')
            # contour = cv2.bitwise_not(contour)
            # while True:
            #     key = cv2.waitKey(1)
            #     _, frame = self.cap.read()
            #     # frame = cv2.addWeighted(frame,self.uservid_weight,contour,1,0)
            #     cv2.imshow(WINDOWNAME, frame)
            
    def multiplayer(self):
        self.show_screen('room')
        self.show_screen('nickname') 
        self.room_name = ROOM + ''.join(self.room)
        print(self.room_name)
        self.createaws()
        if raspi: 
            self.remote_connection.set_conn_info('m', ''.join(self.nickname), ''.join(self.room))
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
        # self.createorjoin = 0
        self.room = ['*','*','*','*','*','*']
        if self.mode == 0:
            self.singleplayer()
        elif self.mode == 1: 
            self.multiplayer()
        elif self.mode == 2:
            self.tutorial()
        else:
            print('error')
            exit(1)

    def test(self):
        # frame = np.zeros(shape=[self.height, self.width, 3], dtype=np.uint8)
        # example_arr = [None, (352, 296), (320, 296), None, None, (416, 160), (296, 112), (256, 120), (352, 120), None, None, (488, 168), None, None, (440, 160)]
        # output = contour_pictures[0]
        # count = 0 
        # for point in example_arr:
        #     if point == None or point[0] > 480 or point[1] > 640:
        #         continue
        #         # cv2.circle(output, (point[0],point[1]), 8, (0, 255, 255), thickness=-1, lineType=cv2.FILLED)
        #     if output[point[0],point[1],0] > 20 and output[point[0],point[1],1] > 20 and output[point[0],point[1],2] > 20:
        #         count +=1
        # for point in example_arr:
        #     if point != None:
        #         cv2.circle(output, (point[0],point[1]), 8, (0, 255, 255), thickness=-1, lineType=cv2.FILLED)
        # print(count)
        # cv2.imshow('test',output)
        # while True:
        #     if cv2.waitKey(0):
        #         break
        # 
        # 
        # 
        # 
        
        
        
        
        # contour = cv2.imread('Output-Contour.jpg')
        # contour = cv2.bitwise_not(contour)
        # print(contour.shape)
        # while True: 
        #     _, frame = self.cap.read()
        #     # print(frame.shape)
        #     # frame = cv2.addWeighted(frame,self.uservid_weight,contour,1,0)
        #     cv2.imshow(WINDOWNAME, frame)
        pass 
    def __del__(self):
        cv2.destroyAllWindows()
        self.client_mqtt.loop_stop()
        self.client_mqtt.disconnect()
        self.voice.stop()
    

def main():
    game = Game()
    game.game()

if __name__ == '__main__':
    main()
