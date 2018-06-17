from umqtt import MQTTClient
from machine import Pin
import machine

led = Pin(2, Pin.OUT, value=1)

# Default MQTT server to connect to
SERVER = "192.168.12.1"
CLIENT_ID = "104"
TOPIC = b"intarnetto/module_" + CLIENT_ID

state = True

def sub_cb(topic, msg):
	global state
	print((topic, msg))
	if msg == b"on":
		led.value(1)
		state = True
		c.publish(TOPIC + "/status", str(state))
	elif msg == b"off":
		led.value(0)
		state = False
		c.publish(TOPIC + "/status", str(state))
	elif msg == b"toggle":
		led.value(not state)
		state = not state
		c.publish(TOPIC + "/status", str(state))
	elif msg == b"state":
		c.publish(TOPIC + "/status", str(state))

c = MQTTClient(CLIENT_ID, SERVER)
# Subscribed messages will be delivered to this callback
c.set_callback(sub_cb)
c.connect()
c.subscribe(TOPIC)
print("Connected to %s, subscribed to %s topic" % (SERVER, TOPIC))

try:
	while 1:
		c.wait_msg()
finally:
	c.disconnect()