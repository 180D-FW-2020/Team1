import paho.mqtt.client as mqtt
import json
connection_string = "ece180d-team1-room-"

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
        
    # 3. call one of the loop*() functions to maintain network traffic flow with the broker.
    client.loop_start()
    # client.loop_forever()


    packet = {
        "username": 'cancel',
        "disconnect": 'suck my balls'
    }
    client.publish(connection_string, json.dumps(packet), qos=1)


    # use subscribe() to subscribe to a topic and receive messages.
    # use publish() to publish messages to the broker.
    # use disconnect() to disconnect from the broker.
    client.loop_stop()
    client.disconnect()