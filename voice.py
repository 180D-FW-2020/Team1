#!/usr/bin/env python3

#requires pyAudio and Speech Recognition conda venv.

import speech_recognition as sr

# obtain audio from the microphone
r = sr.Recognizer()
with sr.Microphone() as source:
    print("Say something!")

    while True:
        audio = r.listen(source)

        # recognize speech using Google Speech Recognition
        output_string = ""
        try:
            output_string =  r.recognize_google(audio)
            print("Google Speech Recognition thinks you said " + output_string)

            keyword = "activate"
            if (keyword.lower() in output_string.lower()):
                print("CALLBACK WE STARTED A POWERUP") #this will need to be fine tuned later

            
        except Exception as e:
            print("please try again")
