#!/usr/bin/env python3

import speech_recognition as sr

# obtain audio from the microphone
r = sr.Recognizer()
with sr.Microphone() as source:
    print("Say something!")

    while True:
        audio = 0
        try:
            audio = r.listen(source,1.5)
        except sr.WaitTimeoutError:
            print("No new words")

        # recognize speech using Google Speech Recognition
        output_string = ""
        try:
            output_string =  r.recognize_google(audio)
            print("Google Speech Recognition thinks you said " + output_string)
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service; {0}".format(e))
        except:
            print("no audio")


        if (output_string=="hello"):
            print("CALLBACK WE STARTED A POWERUP") #this will need to be fine tuned later
