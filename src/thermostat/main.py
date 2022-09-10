try:
    import usocket as socket
except:
    import socket
import ustruct as struct
from ubinascii import hexlify
import esp
import machine
import network


from time import sleep
import socket
import time

try:
    import binascii
except ImportError:
    import ubinascii as binascii
import utime 

from settings import *
from uln2003 import Stepper, FULL_STEP
            
class thermostat:

    def __init__(self,level=17.5):
        self.level = level
        self.motor = Stepper(FULL_STEP,27,33,23,32,delay=5000)
        self.steps_per_degree = 500/(17.75-9)
        self.on_level = 21.5
        self.off_level = 15
    def set_temperature(self,T):
        diff = T -self.level
        steps = abs(self.steps_per_degree*diff)
        if diff<0:
            self.motor.step(steps,1)
        if diff>=0:
            self.motor.step(steps,-1)
        self.level = T

    def on(self):
        self.set_temperature(self.on_level)

    def off(self):
        self.set_temperature(self.off_level)

    def neutral(self):
        self.set_temperature(17.5)

class MQTT(object):
    s = None
    addr = None
    

    def __init__(self, host, port=1883,device_name="Thermostat"):
        self.addr = socket.getaddrinfo(host, port)[0][4]
        self.reset_socket()
        self.device_name = device_name
        self.pid=0
    def reset_socket(self):
        self.s = socket.socket()

    def connect(self):
        address = self.addr
        self.s.connect(address)
        self.s.send(self.mtpConnect(self.device_name))

    def disconnect(self):
        self.s.send(self.mtpDisconnect())
        self.s.close()

    def publish(self, topic, data, sleep=1):
        self.s.send(self.mtpPub(topic, bytes(str(data), 'ascii')))
        if sleep:
            time.sleep(sleep)

    def recv(self, length=4096):
        return binascii.hexlify(self.s.recv(length))

    @staticmethod
    def mtStr(s):
        return bytes([len(s) >> 8, len(s) & 255]) + s.encode('utf-8')

    @staticmethod
    def mtPacket(cmd, variable, payload):
        return bytes([cmd, len(variable) + len(payload)]) + variable + payload

    def mtpConnect(self, name):
        return self.mtPacket(
            0b00010000,
            self.mtStr("MQTT") +  # protocol name
            b'\x04' +  # protocol level
            b'\x00' +  # connect flag
            b'\xFF\xFF',  # keepalive
            self.mtStr(name)
        )

    @staticmethod
    def mtpDisconnect():
        return bytes([0b11100000, 0b00000000])

    def mtpPub(self, topic, data):
        return self.mtPacket(0b00110001, self.mtStr(topic), data)

    def subscribe(self, topic, qos=0):
        assert self.cb is not None, "Subscribe callback is not set"
        pkt = bytearray(b"\x82\0\0\0")
        self.pid += 1
        struct.pack_into("!BH", pkt, 1, 2 + 2 + len(topic) + 1, self.pid)
        #print(hex(len(pkt)), hexlify(pkt, ":"))
        self.s.write(pkt)
        self._send_str(topic)
        self.s.write(qos.to_bytes(1, "little"))
        while 1:
            op = self.wait_msg()
            if op == 0x90:
                resp = self.s.read(4)
                #print(resp)
                assert resp[1] == pkt[2] and resp[2] == pkt[3]
                if resp[3] == 0x80:
                    pass
                return

    def _send_str(self, s):
        self.s.write(struct.pack("!H", len(s)))
        self.s.write(s)

    def _recv_len(self):
        n = 0
        sh = 0
        while 1:
            b = self.s.read(1)[0]
            n |= (b & 0x7f) << sh
            if not b & 0x80:
                return n
            sh += 7

    def set_callback(self, f):
        self.cb = f
    # Wait for a single incoming MQTT message and process it.
    # Subscribed messages are delivered to a callback previously
    # set by .set_callback() method. Other (internal) MQTT
    # messages processed internally.
    def wait_msg(self):
        res = self.s.read(1)
        self.s.setblocking(True)
        if res is None:
            return None
        if res == b"":
            raise OSError(-1)
        if res == b"\xd0":  # PINGRESP
            sz = self.s.read(1)[0]
            assert sz == 0
            return None
        op = res[0]
        if op & 0xf0 != 0x30:
            return op
        sz = self._recv_len()
        topic_len = self.s.read(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = self.s.read(topic_len)
        sz -= topic_len + 2
        if op & 6:
            pid = self.s.read(2)
            pid = pid[0] << 8 | pid[1]
            sz -= 2
        msg = self.s.read(sz)
        self.cb(topic, msg)
        if op & 6 == 2:
            pkt = bytearray(b"\x40\x02\0\0")
            struct.pack_into("!H", pkt, 2, pid)
            self.s.write(pkt)
        elif op & 6 == 4:
            assert 0

    # Checks whether a pending message from server is available.
    # If not, returns immediately with None. Otherwise, does
    # the same processing as wait_msg.
    def check_msg(self):
        self.s.setblocking(False)
        return self.wait_msg()

thremo = thermostat()


def sub_cb(topic, msg):
    if topic == b"boiler/set":
        if msg == b"on":
            print("open")
            thremo.on()
            

        elif msg == b"off":
            print("close")
            thremo.off()
        else:
            try:
                val = float(msg)
                thremo.set_temperature(val)
            except:
                print("invalid temperature")
        print(str(thremo.level))
        conn.publish('boiler/value',str(thremo.level))
    elif topic == b"boiler/value":
        try:
            print("starting: level",float(msg))
            thremo.level = float(msg)
        except:
            print("serious error")
    


def start_cb(topic,msg):

    try:
        print("starting: level",float(msg))
        thremo.level = float(msg)
    except:
        print("serious error")


print("start wifi radio")
station = network.WLAN(network.STA_IF)

station.active(True)
station.connect(wifi_ssid, wifi_passwd)
attempts = 0

while station.isconnected() == False:
  sleep(0.1)
  attempts +=1
  if attempts>100:

        time.sleep(30)
        attempts=0

ap_if = network.WLAN(network.AP_IF)
ap_if.active(False)
print("wifi connected")
conn = MQTT(server)
conn.set_callback(start_cb)
conn.connect()
conn.subscribe("boiler/value")
conn.check_msg()
conn.disconnect()
time.sleep(1)
conn = MQTT(server)
conn.set_callback(sub_cb)
conn.connect()
conn.subscribe("boiler/set")
#conn.publish('light/stairs/set','toggle')
try:
    while True:
        conn.check_msg()
        if station.isconnected() == False:
            station = network.WLAN(network.STA_IF)
            station.active(True)
            station.connect(wifi_ssid, wifi_passwd)
            attempts = 0

            while station.isconnected() == False:

                time.sleep(0.1)

                attempts +=1

                if attempts>100:
                        time.sleep(30)
        sleep(5)
except:
    machine.reset()



#loop.create_task(encoder_loop(enc))
#try:
