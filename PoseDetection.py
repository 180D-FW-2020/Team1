import cv2
import numpy as np
import time as t

cap = cv2.VideoCapture(0)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
time = 75
radius = 95
blue = (255,0,0)
red = (0, 0, 255)
thickness = 2
circle_center = (int(w/2), int(h/2)) 
rect_start = (int(w/2)-radius, int(h/2)+radius)
rect_end = (int(w/2)+radius, int(h/2)+4*radius)
print(circle_center,rect_start,rect_end)

sample_points = [(int(w/2), int(h/2)), (int(w/2),int(h/2)+radius+5)]
score = 0
while True:
    _, frame = cap.read()
    frame = cv2.circle(frame, sample_points[0],8, red, thickness=-1, lineType=cv2.FILLED)
    frame = cv2.circle(frame, circle_center, radius, blue, thickness)
    frame = cv2.rectangle(frame, rect_start, rect_end, blue, thickness)
    if time >= 0:
        cv2.putText(frame, "time remaining {}".format(time), (50, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
        time -= 1 
    elif time == -1: 
        for point in sample_points:
            if np.sqrt((circle_center[0]-point[0])**2 + (circle_center[1]-point[1])**2) <= radius:
                score += 1
            elif point[0] > rect_start[0] and point[0] < rect_start[0] and point[1] > rect_start[1] and point[1] < rect_start[1]:
                score += 1
        time -= 1
    cv2.putText(frame, "Score: {}".format(score), (500, 50), cv2.FONT_HERSHEY_COMPLEX, .8, (255, 50, 0), 2, lineType=cv2.LINE_AA)
        
    cv2.imshow('FramePlusCircle', frame)
    if cv2.waitKey(1) == ord('q'):
        break
cap.release()