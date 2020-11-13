# file to run the program
"""
overall handler for the output to user
@TODO: create overall skeleton of function @NOTE DONE 
@TODO: figure out how to add contours (DONE), voice/speech, gesture into it
@TODO: shown below: want to have a UI change while the score is being tallied 
@TODO: go to the "next level"
@NOTE: consider cv2.waitKey(0) 
"""
from PoseEstimation import *
from ContourDetection import *
import cv2
import time 
import numpy as np
cap = cv2.VideoCapture(0)
cv2.namedWindow('Hole in the Wall!', cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty('Hole in the Wall!',cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
# cv2.imshow("window", img)
pose = PoseEstimation() # grab the object
score = 0
def show_beginning_screen():
    frame = np.zeros(shape=[480, 640, 3], dtype=np.uint8)
    cv2.putText(frame, "HOLE IN THE WALL", (140, 220), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
    cv2.putText(frame, "Press any key to start...", (140, 300), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
    cv2.imshow('Hole in the Wall!', frame)
    while True:
        if cv2.waitKey(0): 
            break
"""
showScore(frame): show the score
input: 
    frame -> the video frame that we want the score to go on top of
output: 
    frame -> the modified frame with the score on it
@TODO: 
@NOTE: 
@NOTE: 
"""
def showScore(frame):
    cv2.putText(frame, "Score: {}".format(score), (500, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
    return frame

"""
showTime(frame, start_time): show the time remaining  
input: 
    frame -> the video frame that we want the score to go on top of
output: 
    frame -> the modified frame with the score on it
@TODO: implement timinig mechanism
@NOTE: already have some code written for it so I can get this done
@NOTE: also may be something that'll probably be overridden later 
"""
def showTime(frame, start_time):
    time_remaining = TIMER_THRESHOLD - int(time.perf_counter()-start_time)
    cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)

    return frame, time_remaining

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
def level(number):
    start_time = time.perf_counter()
    frame = np.zeros(shape=[480, 640, 3], dtype=np.uint8)
    cv2.putText(frame, "Level {}".format(number), (240, 320), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
    cv2.imshow('Hole in the Wall!', frame)
    while True:
        time_remaining = 3 - int(time.perf_counter()-start_time)
        if cv2.waitKey(0) or time_remaining <=0: 
            break
    total_frames = 0 
    start_time = time.perf_counter()
    while True:
        _, frame = cap.read()
        frame = showScore(frame)
        frame, time_remaining = showTime(frame, start_time)
        cv2.imshow('Hole in the Wall!', frame)
        total_frames += 1
        if cv2.waitKey(1) == ord('q'): 
            break
        if time_remaining <= 0: # @TODO
            frame, points = pose.getPoints(frame)
            while True:
                cv2.imshow('Hole in the Wall!', frame)
                if cv2.waitKey(1) == ord('q'):
                    return
    print(total_frames)
def start_game():
    level_number = 1
    show_beginning_screen()
    while True:
        level(level_number)
        level_number += 1
    
start_game()