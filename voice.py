#requires pyAudio and Speech Recognition conda venv.

import speech_recognition as sr
import time


#Class to recognize commands. Listen/stop are used to control it being active.
#dispatch should be called in any free time the program has (where actual listening is performed)
class commandRecognizer:
    def __init__(self, command_dictionary):
        self.command_dictionary = command_dictionary
        self.r = sr.Recognizer()
        self.m = sr.Microphone()
        with self.m as source:
            self.r.adjust_for_ambient_noise(source)  # we only need to calibrate once, before we start listening

    def listen(self):
        self.stop_listening = self.r.listen_in_background(self.m, self.rec, phrase_time_limit=2)
    
    def stop(self):
        self.stop_listening(wait_for_stop=False)

    def rec(self, recognizer, audio):
        # received audio data, now we'll recognize it using Google Speech Recognition
        try:
            # for testing purposes, we're just using the default API key
            # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
            # instead of `r.recognize_google(audio)`
            output_string=recognizer.recognize_google(audio)
            print("Google Speech Recognition thinks you said " + recognizer.recognize_google(audio))
            #check if the keyword is present in any of the speech
            for key in self.command_dictionary:
                if (key.lower() in output_string.lower()):
                    self.command_dictionary[key]()

        except sr.UnknownValueError:
            # print("Google Speech Recognition could not understand audio")
            pass
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service; {0}".format(e))



#example usecase

#example callbacks for commands/pause/any functionality we need
# def ex1():
#     print("activate command called")
# def ex2():
#     print("help command called")

#Example keywords being linked to the callbacks
# keywords_example = {
#     "activate" : ex1,
#     "help" : ex2
# }

# c = commandRecognizer(keywords_example)
# c.listen()

# while True:
#     print("waiting")
#     time.sleep(0.2)
