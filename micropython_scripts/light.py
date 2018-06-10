import socket, machine, time, urequests

led = machine.Pin(3, machine.Pin.OUT)

def send_status():
    try:
        response = urequests.get(req % led.value())
        response.close()
    except Exception as e:
        print(str(e))
        pass

req = "http://192.168.12.1:8080/status_light?lit=%d"
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)
while True:
    HEAD = b"""\
HTTP/1.0 200 OK

%d
"""
    conn, addr = s.accept()
    request = conn.recv(1024)
    request = str(request)
    LEDON = request.find('/light?lit=1')
    LEDOFF = request.find('/light?lit=0')
    STATUS = request.find('/status')
    if LEDON == 6:
        led.on()
    if LEDOFF == 6:
        led.off()
    conn.write(HEAD % led.value())
    conn.close()
    send_status()
    time.sleep(1)