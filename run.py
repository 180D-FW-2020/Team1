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

img = cv2.imread(r'.\test_contour.jpg')
img = cv2.bitwise_not(img)
TIMER_THRESHOLD = 5

cap = cv2.VideoCapture(0)
# _, frame = cap.read()
# print((frame+img).shape)
# cv2.waitKey(0)
# exit(1)
width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

WINDOWNAME = 'Hole in the Wall!'
cv2.namedWindow(WINDOWNAME, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(WINDOWNAME,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
# cv2.imshow("window", img)
pose = PoseEstimation() # grab the object
detector = ContourDetection()
def show_beginning_screen():
    frame = np.zeros(shape=[480, 640, 3], dtype=np.uint8)
    cv2.putText(frame, "HOLE IN THE WALL", (140, 220), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
    cv2.putText(frame, "Press any key to start...", (140, 300), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
    cv2.imshow(WINDOWNAME, frame)
    while True:
        if cv2.waitKey(0): 
            break

 
def editFrame(frame, start_time, score):
    original = np.copy(frame)
    time_remaining = TIMER_THRESHOLD - int(time.perf_counter()-start_time)
    # if time_remaining >= 8:
    #     contour_weight = 1
    # elif time_remaining >= 6:
    #     contour_weight = 0.7
    # elif time_remaining >= 4:
    #     contour_weight = 0.5
    # elif time_remaining >= 2:
    #     contour_weight = 0.25
    # else:
    #     contour_weight = 0

    # frame = cv2.addWeighted(frame,contour_weight,img,1-contour_weight,0)
    if time_remaining <= 0:
        time_remaining = 0
    frame = cv2.add(frame,img)
    cv2.putText(frame, "Time Remaining: {}".format(time_remaining), (10, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
    cv2.putText(frame, "Score: {}".format(score), (500, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)

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
def level(number, score):
    start_time = time.perf_counter()
    frame = np.zeros(shape=[480, 640, 3], dtype=np.uint8)
    cv2.putText(frame, "Level {}".format(number), (240, 320), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
    cv2.imshow(WINDOWNAME, frame)
    while True:
        time_remaining = 3 - int(time.perf_counter()-start_time)
        if cv2.waitKey(0) or time_remaining <=0: 
            break
    total_frames = 0 
    start_time = time.perf_counter()
    while True:
        _, frame = cap.read()
        # frame = showScore(frame)
        frame, time_remaining, original = editFrame(frame, start_time, score)
        cv2.imshow(WINDOWNAME, frame)
        total_frames += 1
        if cv2.waitKey(1) == ord('q'): 
            break
        if time_remaining <= 0: # @TODO
            frame, points = pose.getPoints(original)
            if detector.isWithinContour(points, 'test_contour.jpg'):
                score += 1
            while True:
                frame, time_remaining, original = editFrame(original, start_time, score) #@TODO: need to fix time going under 0 -- fix in editFrame function
                cv2.imshow(WINDOWNAME, frame)
                if cv2.waitKey(1) == ord('q'):
                    return score
    print(total_frames)
    return score
def start_game():
    score = 0
    level_number = 1
    show_beginning_screen()
    while True:
        score = level(level_number,score)
        level_number += 1
    
start_game()