# Intarnetto
Simple IoT server made with Python Bottle

## Current status
Temperature is displayed, windows are checked, lights get lit and unlit, you can enslave mpd. It works, I guess.

## Requirements
+ Some sensor modules
+ A MQTT broker

## Basic configuration

```
[server]
ip = 0.0.0.0
port = 8080
mqtt_broker = 0.0.0.0
broker_port = 1883

[room_name]
type = room
color = blue

[module_name] # If uses MQTT, it has to be the same as the client ID
type = temperature
ip = 192.168.12.101
active = yes
room = salotto

```
