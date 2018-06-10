import machine, urequests

pin = machine.Pin(3, machine.Pin.IN)

req = "http://192.168.12.1:8080/window?closed=" + str(pin.value())
print(req)
try:
	response = urequests.get(req)
	response.close()
except:
	pass
