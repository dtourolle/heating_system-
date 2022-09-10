import paho.mqtt.subscribe as subscribe
import paho.mqtt.publish as publish
import datetime as dt
import time
import mariadb
from config import *
import numpy as np


rooms = ['office','guestroom','kitchen','tv_area', 'workshop']

# on first start close all valves, this is to ensure system is in a known state.
for r in rooms:
    publish.single('radiator/'+r+'/set', "close", hostname=server)

# for logging of historic data connect to a database
conn = mariadb.connect(
    user=user,
    password=password,
    host="localhost",
    port=3306,
    database="HOME"

)

cursor = conn.cursor()

# initialise the state
state = {r:'close' for r in rooms}
temperature ={r:0 for r in rooms}
set_t ={r:21.5 for r in rooms} # assume a temperature of 21.5 until set is read from MQTT


time.sleep(10)

satisfied={r:True for r in rooms} #this variable tracks how many rooms need the boiler enabled
min_required_rooms = 1 # the minimum number of rooms before the boiler is enabled.

boiler_state = 'unknown'

start_at = 7
stop_at= 23

thermostat_boiler_on = 23.5
thermostat_boiler_off = 7
thermostat_deepsleep =9


while True:
    mean_t=0
    tolerance=0.1
    hour = dt.datetime.now().hour



    for r in rooms:
        print(r)
        msg = subscribe.simple(r+"/temperature/set",hostname=server,retained=True)
        old = set_t[r]
        set_t[r]=float(msg.payload)
        if set_t[r] != old:
            cursor.execute("INSERT INTO events (room,event,time) VALUES (?, ?, ?)",  (r, 'thermo set: '+str(set_t[r]),dt.datetime.now()))
        print(r,set_t[r])
        msg = subscribe.simple("temperature/"+r,hostname=server,retained=True)
        print('current state',state)
        temperature[r] = float(msg.payload)
        cursor.execute("INSERT INTO temperature (room,reading,time) VALUES (?, ?, ?)",  (r, temperature[r],dt.datetime.now()))
    print(hour,temperature)


    for r in rooms:
        if temperature[r] < (set_t[r] -tolerance) and temperature[r]!=0:
            if hour >= start_at and hour < stop_at:
                if state[r] == 'close':
                    publish.single("radiator/"+r+"/set", "open", hostname=server)
                    state[r]='open'
                    cursor.execute("INSERT INTO events (room,event,time) VALUES (?, ?, ?)",  (r, 'radiator open',dt.datetime.now()))
                    print(r,'open')
            satisfied[r] = False

        if temperature[r] > (set_t[r]+tolerance) and temperature[r]!=0:
            if hour >= start_at and hour < stop_at:
                if state[r] == 'open':
                    publish.single("radiator/"+r+"/set", "close", hostname=server)
                    state[r]='close'
                    cursor.execute("INSERT INTO events (room,event,time) VALUES (?, ?, ?)",  (r, 'radiator close',dt.datetime.now()))
                    print(r,'close')
            satisfied[r]=True
        
        if hour == stop_at and state[r] == 'open':
                publish.single("radiator/"+r+"/set", "close", hostname=server)
                state[r]='close'
                cursor.execute("INSERT INTO events (room,event,time) VALUES (?, ?, ?)",  (r, 'radiator close',dt.datetime.now()))
                print(r,'Night time off close')
    print("rooms satisfaction",list(satisfied.values()))
    
    if hour >=start_at and hour < stop_at:
        if sum(np.array(list(satisfied.values()))==False)>=min_required_rooms:
            if boiler_state != 'ON':
                publish.single("boiler/set", thermostat_boiler_on, hostname=server)
                cursor.execute("INSERT INTO events (room,event,time) VALUES (?, ?, ?)",  ('boiler', 'ON',dt.datetime.now()))
                boiler_state = 'ON'
        else:
            if boiler_state != 'OFF':
                publish.single("boiler/set", thermostat_boiler_off, hostname=server)
                cursor.execute("INSERT INTO events (room,event,time) VALUES (?, ?, ?)",  ('boiler', 'OFF',dt.datetime.now()))
                boiler_state = 'OFF'
    else:
        if boiler_state != 'SLEEP':
           publish.single("boiler/set", thermostat_deepsleep, hostname=server)
           cursor.execute("INSERT INTO events (room,event,time) VALUES (?, ?, ?)",  ('boiler', 'SLEEP',dt.datetime.now()))
           boiler_state = 'SLEEP'
    conn.commit() 
    publish.single("radiator/controller/alive", str(dt.datetime.now()), hostname=server)
    time.sleep(30)

