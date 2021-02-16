import paho.mqtt.client as mqtt
import json
import sys
import datetime
from optparse import OptionParser
from gesture_detector import gestureRecognizer

connection_string = "ece180d-team1-room-"
accel_thres = 200

usage_msg = '''%prog [mode] [username] [roomcode - multiplayer only]
connect using username and roomcode from main game.'''

parser = OptionParser(usage=usage_msg)
parser.add_option('-m', '--mode', dest='mode', default='s', help='single player \'s\' or multiplayer \'m\', default = single player', metavar="MODE")
parser.add_option('-u', '--username', dest='username', default='', help='use same username as main game', metavar="USER")
parser.add_option('-r', '--roomcode', dest='roomcode', default='', help='use same roomcode as main game', metavar="ROOM")

options, args = parser.parse_args(sys.argv[1:]) 

if options.mode != 's' and options.mode != 'm': 
    parser.error("Please select a valid mode: single player \'s\' or multiplayer \'m\'")

#multiplayer mode (room code)
if options.roomcode != '': #todo: check if room code is 6 characters 
    if len(options.roomcode) != 6: 
        parser.error("Please enter a 6 character room code for multiplayer mode.")
    if options.username == '':
        parser.error("Please enter username for multiplayer mode.")
    username = str(options.username)
    roomcode = str(options.roomcode) 
    connection_string += roomcode
    print("Welcome to multiplayer Hole-in-the-Wall!")
elif options.roomcode == '' and options.mode == 'm':
    parser.error("Please enter roomcode for multiplayer mode.")
# single player mode 
elif options.roomcode == '' and options.mode == 's': 
    if options.username != '': 
        username = str(options.username) 
    else: 
        username = "singleplayer"
    print("Welcome to single player Hole-in-the-Wall!")

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

if __name__ == "__main__": 
    # 1. create a client instance.
    client = mqtt.Client()
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

    print("Calibrating acceleration... ")

    count = 0 
    accel_base = 0 

    start = datetime.datetime.now()
    elapsed_ms = 0
    previous_elapsed_ms = 0

    while elapsed_ms < 1.5 * 1000 * 2:
        begin = [] + n.collect()
        accel_base += (abs(begin[0]) + abs(begin[1]) + abs(begin[2])) / 3
        previous_elapsed_ms = elapsed_ms
        elapsed_ms = (datetime.datetime.now() - start).total_seconds() * 1000
        count += 1

    accel_base = accel_base/count 

    print("Base acceleration: " + str(accel_base))

    while True:
        #Example method for sending a gesture
        check = [] + n.collect() 
        accel_sum = (abs(check[0]) + abs(check[1]) + abs(check[2])) / 3
        if(accel_sum - accel_base > accel_thres): 
            print("Detected motion...")
            prediction = n.classify()
            # print(prediction)
            if(prediction != "negative_trim" and last_classification != prediction): 
                packet = {
                "username": username,
                "gesture": prediction
                }
                client.publish(connection_string, json.dumps(packet), qos=1)
            last_classification = prediction
        pass

    # use subscribe() to subscribe to a topic and receive messages.
    # use publish() to publish messages to the broker.
    # use disconnect() to disconnect from the broker.
    client.loop_stop()
    client.disconnect()
