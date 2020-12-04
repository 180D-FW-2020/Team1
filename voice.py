#requires pyAudio and Speech Recognition conda venv.

import speech_recognition as sr

#Class to recognize commands. Listen/stop are used to control it being active.
#dispatch should be called in any free time the program has (where actual listening is performed)
class commandRecognizer:
    def __init__(self, command_dictionary):
        self.command_dictionary = command_dictionary
        self.active = False

    def listen(self):
        self.active = True
    
    def stop(self):
        self.active = False

    def dispatch(self):
        if self.active:
            # obtain audio from the microphone
            r = sr.Recognizer()
            with sr.Microphone() as source:
                print("Say something!")

                audio = r.listen_in_background(source)

                # recognize speech using Google Speech Recognition
                output_string = ""
                try:
                    output_string =  r.recognize_google(audio)
                    print("Google Speech Recognition thinks you said " + output_string)

                    #check if the keyword is present in any of the speech
                    for key in self.command_dictionary:
                        if (key.lower() in output_string.lower()):
                            self.command_dictionary[key]()

                except Exception as e:
                    print("please try again")


#example usecase

#example callbacks for commands/pause/any functionality we need
def ex1():
    print("activate command called")
def ex2():
    print("help command called")

#Example keywords being linked to the callbacks
keywords_example = {
    "activate" : ex1,
    "help" : ex2
}

c = commandRecognizer(keywords_example)
c.listen()
while True:
    c.dispatch()