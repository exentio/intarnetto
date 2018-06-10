import dht, machine, urequests

d = dht.DHT11(machine.Pin(2))

def temp():
	d.measure()
	return d.temperature()

def hum():
	d.measure()
	return d.humidity()

req = "http://192.168.12.1:8080/temperature?temp=" + str(temp()) + "&hum=" + str(hum())
print(req)
try:
	response = urequests.get(req)
	response.close()
except:
	pass
