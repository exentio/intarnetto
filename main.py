#!/bin/python
import configparser, time, json, requests, os, socket
from bottle import route, request, run, Jinja2Template, jinja2_view, static_file, GeventServer, response, get, HTTPResponse
from gevent import monkey; monkey.patch_all()
from gevent import sleep
from mpd import MPDClient

# Get current time in seconds
sec_time = lambda: int(time.time())
config = configparser.ConfigParser()
modules = []
rooms = []

def parse_bool(s):
	if str(s).lower() in ('yes', 'true', 't', 'y', '1'):
		return True
	elif str(s).lower() in ('no', 'false', 'f', 'n', '0'):
		return False

# Base module class
class Module:
	def __init__(self, code, cat, ip, room):
		self.code = code
		self.cat = cat
		self.ip = ip
		self.room = room
		self.update_time = None

# Specialized modules
class TempModule(Module):
	def __init__(self, code, cat, ip, room, temp=None, hum=None):
		Module.__init__(self, code, cat, ip, room)
		self.temp = temp
		self.hum = hum

	def set_none(self):
		self.temp = None
		self.hum = None

class WinModule(Module):
	def __init__(self, code, cat, ip, room, closed=False):
		Module.__init__(self, code, cat, ip, room)
		self.closed = closed

	def set_none(self):
		self.closed = None

class LightModule(Module):
	def __init__(self, code, cat, ip, room, lit=None):
		Module.__init__(self, code, cat, ip, room)
		self.lit = lit

	def set_none(self):
		self.lit = None

	def toggle(self):
		try:
			status = parse_bool(requests.get("http://" + self.ip + "/light?lit=" + str(int(not self.lit)), timeout=5).text.replace("\n", ""))
			return status
		except:
			pass
		return None

class MpdControl(Module):
	def __init__(self, code, cat, ip, room):
		Module.__init__(self, code, cat, ip, room)
		self.client = MPDClient()
		self.client.timeout = 10
		self.client.connect(self.ip, 6600)
		self.playing = self.client.status()["state"]
		self.title = self.client.currentsong()["title"]
		self.artist = self.client.currentsong()["artist"]

	def set_none(self):
		self.title = None
		self.artist = None
		self.playing = None

	def toggle(self):
		try:
			if self.client.status()["state"] == "play":
				self.client.pause(1)
			elif self.client.status()["state"] == "pause":
				self.client.pause(0)
			elif self.client.status()["state"] == "stop":
				self.client.play()
			self.playing = self.client.status()["state"]
			return self.playing
		except Exception as e:
			print(str(e))
		return None

# Room class
class Room:
	def __init__(self, name, module_qty, color="wht"):
		self.name = name
		self.module_qty = module_qty
		self.color = color

# Configuration parser and init
def init_config():
	global config
	global modules
	global rooms

	config.read('config.ini')
	for sec in config.sections():
		try:
			if config[sec]['active'] == 'yes':

				if config[sec]['type'] == "temperature":
					mMod = TempModule(sec, config[sec]['type'], config[sec]['ip'], config[sec]['room'])
				elif config[sec]['type'] == 'window':
					mMod = WinModule(sec, config[sec]['type'], config[sec]['ip'], config[sec]['room'])
				elif config[sec]['type'] == 'light':
					mMod = LightModule(sec, config[sec]['type'], config[sec]['ip'], config[sec]['room'])
				elif config[sec]['type'] == 'mpd':
					mMod = MpdControl(sec, config[sec]['type'], config[sec]['ip'], config[sec]['room'])

				modules.append(mMod)
		except KeyError:
			continue
		except Exception as e:
			print(str(e))

	for sec in config.sections():
		try:
			if config[sec]['type'] == 'room':
				mModule_qty = 0
				for module in modules:
					if module.room == sec:
						mModule_qty += 1
				mRoom = Room(sec, mModule_qty, config[sec]['color'])
				rooms.append(mRoom)
		except KeyError:
			continue
		except Exception as e:
			print(str(e))

	# Pass variables to the Jinja template
	Jinja2Template.defaults['modules'] = modules
	Jinja2Template.defaults['rooms'] = rooms

# Serve main page
@route('/')
@jinja2_view('html/index.htm')
def index():
	return

# Serve static files like CSS, JS and images
@route('/<filename:path>')
def send_static(filename):
	return static_file(filename, root='.')

# Server-Side Events
@route('/events')
def events():
	response.content_type = 'text/event-stream'
	response.cache_control = 'no-cache'

	# Set client-side auto-reconnect timeout, ms.
	yield 'retry: 100\n\n'

	json_data = {}
	temp_json = {}

	# Keep connection alive no more then... (s)
	end = time.time() + 60
	while time.time() < end:
		for module in modules:
			# If a module's parameters are set to None, it means it died somehow
			# The mpd module works in real time with an actual connection
			# Thus, it doesn't need to be checked
			if module.cat != "mpd" and (module.update_time is None or (sec_time() - module.update_time) > 60):
				module.set_none()
				if module.cat == "light":
					try:
						module.lit = parse_bool(requests.get("http://" + module.ip + "/status", timeout=5).text.replace("\n", ""))
						module.update_time = sec_time()
					except:
						pass

			if module.cat == 'temperature':
				temp_json[module.code] = {'cat' : module.cat, 'temp' : module.temp, 'hum' : module.hum}
			elif module.cat == 'window':
				temp_json[module.code] = {'cat' : module.cat, 'closed' : module.closed}
			elif module.cat == 'light':
				temp_json[module.code] = {'cat' : module.cat, 'lit' : module.lit}
			elif module.cat == 'mpd':
				# The mpd module gets update every time a SSE is sent
				module.playing = module.client.status()["state"]
				module.title = module.client.currentsong()["title"]
				module.artist = module.client.currentsong()["artist"]

				temp_json[module.code] = {'cat' : module.cat, 'playing' : module.playing, 'title' : module.title, 'artist' : module.artist}

		# Data is sent only when it gets updated
		if json.dumps(temp_json) != json_data:
			json_data = json.dumps(temp_json)
			yield 'data: ' + json_data + '\n\n'
		sleep(0.3)

# Get temperature data from a module
# It's sent by the module, not grabbed by the server
# because the module goes on deep sleep mode every 30 seconds
@get('/temperature')
def set_temperature():
	# The module is identified by its IP address
	client_ip = request.environ.get('REMOTE_ADDR')
	for module in modules:
		if module.ip == client_ip and module.cat == 'temperature':
			module.temp = request.query.temp
			module.hum = request.query.hum
			# Time it was last updated
			module.update_time = sec_time()
			#print('Temperature: ' + module.temp + '\nHumiduty: ' + module.hum)
			break

# Get the window status from a module
# It's sent by the module, not grabbed by the server
# because the module goes on deep sleep mode every 15 seconds
@get('/window')
def set_closed():
	# The module is identified by its IP address
	client_ip = request.environ.get('REMOTE_ADDR')
	for module in modules:
		if module.ip == client_ip and module.cat == 'window':
			module.closed = parse_bool(request.query.closed)
			# Time it was last updated
			module.update_time = sec_time()
			#print('Closed: ' + str(module.closed))
			break

# Toggle a light module
# The module code is sent as a GET parameter
@get('/toggle_light')
def toggle_light():
	# Get the "code" parameter from the GET request
	module_code = request.query.code
	for module in modules:
		if module.code == module_code and module.cat == 'light':
			module.lit = module.toggle()
			# Time it was last updated
			module.update_time = sec_time()
			#print('Lit: ' + str(module.lit))
			break
	# It's needed by the JS code
	return HTTPResponse(status=200, body="Done")

# Get info from a mpd module
# The module code and the action required are sent as GET parameters
@get('/toggle_mpd')
def set_mpd_status():
	# Get the "code" parameter from the GET request
	module_code = request.query.code
	# Get the "action" parameter from the GET request
	action = request.query.action
	for module in modules:
		if module.code == module_code and module.cat == 'mpd':
			if action == "toggle":
				module.playing = module.toggle()
			elif action == "prev":
				module.client.previous()
			elif action == "next":
				module.client.next()
			#print('Status: ' + str(module.playing))
			break
	# It's needed by the JS code
	return HTTPResponse(status=200, body="Done")

print("Initializing configuration... ", end='', flush=True)
init_config()
print("done!")

# Remember kids, loopback and 0.0.0.0 are different stuff
run(server=GeventServer, host='0.0.0.0', port=8080)