import configparser, json, time, threading, signal, sys, os
import paho.mqtt.client as mqtt
from mpd import MPDClient
from argparse import ArgumentParser
from daemon import Daemon

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

def daemon_signal_handler(signal, frame):
	daemon.stop()

def signal_handler(signal, frame):
	sys.exit(0)

def block_print():
 	   sys.stdout = open(os.devnull, 'w')

def enable_print():
	sys.stdout = sys.__stdout__

class RunDaemon(Daemon):
	def run(self):
		mqtt_c.loop_start()
		forever.wait()

parser = ArgumentParser()
parser.add_argument("-b", "--broker",
	dest="mqtt_broker",default="0.0.0.0",
	help="Set the MQTT broker IP")
parser.add_argument("-p", "--broker_port",
	dest="broker_port", default=1883,
	help="Set the MQTT broker port")
parser.add_argument("-c", "--client_id",
	dest="CLIENT_ID", default="mpd",
	help="Set the MQTT client ID for the daemon")
parser.add_argument("-i", "--mpd_ip",
	dest="mpd_ip", default="localhost",
	help="Set the mpd server IP")
parser.add_argument("-m", "--mpd_port",
	dest="mpd_port", default=6600,
	help="Set mpd server port")
parser.add_argument("-k", "--kill",
	dest="kill_daemon", action='store_true',
	help="Kill the running daemon")
parser.add_argument("--no-daemon",
	dest="no_daemon", action='store_true',
	help="Execute without daemonizing")

args = parser.parse_args()

if not args.kill_daemon:
	mqtt_broker = args.mqtt_broker
	broker_port = args.broker_port
	CLIENT_ID = args.CLIENT_ID
	mpd_ip = args.mpd_ip
	mpd_port = args.mpd_port

	mpd = MPDClient()
	mpd.timeout = 10
	mpd.connect(mpd_ip, mpd_port)

	mqtt_c = mqtt.Client(CLIENT_ID)
	mqtt_c.connect(mqtt_broker, port=broker_port)
	mqtt_c.subscribe("mpd/module_" + CLIENT_ID)
	mqtt_c.on_message=on_mqtt_message

	forever = threading.Event()

if args.no_daemon:
	block_print()
	daemon = RunDaemon('./.mqtt-mpd.pid')
	enable_print()
else:
	daemon = RunDaemon('./.mqtt-mpd.pid')

if args.kill_daemon:
	daemon.stop()
elif args.no_daemon:
	try:
		block_print()
		daemon.stop()
	finally:
		enable_print()
		signal.signal(signal.SIGINT, signal_handler)
		print('Press Ctrl+C to close.')
		daemon.run()
else:
	signal.signal(signal.SIGQUIT, daemon_signal_handler)
	daemon.start()