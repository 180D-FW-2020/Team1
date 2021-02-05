import paho.mqtt.client as mqtt
import json
import sys
from optparse import OptionParser
from gesture_detector import * 
connection_string = "ece180d-team1-room-"

usage_msg = '''%prog [username] [roomcode]
connect using username and roomcode from main game.'''

parser = OptionParser(usage=usage_msg)
parser.add_option('-m', '--mode', dest='mode', default='s', help='single player \'s\' or multiplayer \'m\', default = single player', metavar="MODE")
parser.add_option('-u', '--username', dest='username', default='', help='use same username as main game', metavar="USER")
parser.add_option('-r', '--roomcode', dest='roomcode', default='', help='use same roomcode as main game', metavar="ROOM")

options, args = parser.parse_args(sys.argv[1:]) 

# single player mode 
if not options.mode or if options.mode == 's': 
    if options.username != '': 
        username = options.username
    else: 
        username = "singleplayer"
    if options.roomcode: 
        parser.error("No roomcode for single player.")
    
# multiplayer mode 
elif options.mode == 'm': 
    if options.username == '': 
        parser.error("Please enter username.")
    if options.roomcode == '': 
        parser.error("Please enter roomcode.")

    username = str(options.username)
    roomcode = str(options.roomcode) 

    connection_string += roomcode
else: 
    parser.error("Please select a valid mode: single player \'s\' or multiplayer \'m\'")


# 0. define callbacks - functions that run when events happen.
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connection returned result: "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(connection_string, qos=1)
    
# The callback of the client when it disconnects.
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print('Unexpected Disconnect')
    else:
        print('Expected Disconnect')
            
# The default message callback.
# (you can create separate callbacks per subscribed topic)
def on_message(client, userdata, message):
    print('Received message: "' + str(message.payload) + '" on topic "' +
    message.topic + '" with QoS ' + str(message.qos))
            
# 1. create a client instance.
client = mqtt.Client()
# add additional client options (security, certifications, etc.)
# many default options should be good to start off.
# add callbacks to client.
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message


# 2. connect to a broker using one of the connect*() functions.
client.connect_async('broker.hivemq.com')
# client.connect("mqtt.eclipse.org")

n = gestureRecognizer() 
last_classification = "negative_trim"
    
# 3. call one of the loop*() functions to maintain network traffic flow with the broker.
client.loop_start()
# client.loop_forever()

# print(username, roomcode, connection_string)

while True:
    #Example method for sending a gesture
    # print("before")
    prediction = n.classify()
    # print(prediction)
    if(prediction != "negative_trim" and last_classification != prediction): 
        packet = {
        "username": username,
        "gesture": prediction
        }
        client.publish(connection_string, json.dumps(packet), qos=1)
    # print("after")
    last_classification = prediction
    pass

# use subscribe() to subscribe to a topic and receive messages.
# use publish() to publish messages to the broker.
# use disconnect() to disconnect from the broker.
client.loop_stop()
client.disconnect()