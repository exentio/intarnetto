import configparser, json, time, signal, sys, threading
import paho.mqtt.client as mqtt
from mpd import MPDClient
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("-b", "--broker",
	dest="mqtt_broker",default="0.0.0.0",
	help="MQTT broker IP")
parser.add_argument("-p", "--broker_port",
	dest="broker_port", default=1883,
	help="MQTT broker port")
parser.add_argument("-c", "--client_id",
	dest="CLIENT_ID", default="mpd",
	help="MQTT client ID")
parser.add_argument("-i", "--mpd_ip",
	dest="mpd_ip", default="localhost",
	help="mpd server IP")
parser.add_argument("-m", "--mpd_port",
	dest="mpd_port", default=6600,
	help="mpd server port")

args = parser.parse_args()

mqtt_broker = args.mqtt_broker
broker_port = args.broker_port
CLIENT_ID = args.CLIENT_ID
mpd_ip = args.mpd_ip
mpd_port = args.mpd_port

mpd = MPDClient()
mpd.timeout = 10
mpd.connect(mpd_ip, mpd_port)

def mpd_check():
	try:
		mpd.status()
	except:
		mpd.connect(mpd_ip, mpd_port)

def get_status():
	mpd_check()
	state = mpd.status()["state"]
	title = mpd.currentsong()["title"]
	artist = mpd.currentsong()["artist"]
	data = {'playing' : state,'title' : title, 'artist' : artist}
	return json.dumps(data)

def on_mqtt_message(client, userdata, message):
	topic = "mpd/module_" + CLIENT_ID
	if message.topic == topic:
		m_message = str(message.payload.decode("utf-8"))
		if m_message == "toggle":
			if mpd.status()["state"] == "play":
				mpd_check()
				mpd.pause()
			else:
				mpd_check()
				mpd.play()
			mqtt_c.publish(topic + "/status", get_status())
		elif m_message == "next":
			mpd_check()
			mpd.next()
			mqtt_c.publish(topic + "/status", get_status())
		elif m_message == "prev":
			mpd_check()
			mpd.previous()
			mqtt_c.publish(topic + "/status", get_status())
		elif m_message == "state":
			mpd_check()
			mqtt_c.publish(topic + "/status", get_status())

mqtt_c = mqtt.Client(CLIENT_ID)
mqtt_c.connect(mqtt_broker, port=broker_port)
mqtt_c.subscribe("mpd/module_" + CLIENT_ID)
mqtt_c.on_message=on_mqtt_message
mqtt_c.loop_start()

def signal_handler(signal, frame):
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
print('Press Ctrl+C to close.')
forever = threading.Event()
forever.wait()