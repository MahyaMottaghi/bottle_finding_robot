#!/usr/bin/python3
from __future__ import print_function, division
import serial
import time
import brickpi3
import random

#BP = brickpi3.BrickPi3()
#BP.set_sensor_type(BP.PORT_1, BP.SENSOR_TYPE.EV3_COLOR_COLOR)
# COLOR IDs: 0=None, 1=Black, 2=Blue, 3=Green, 4=Yellow, 5=Red, 6=White, 7=Brown
#color = ["None", "Black", "Blue", "Green", "Yellow", "Red", "White", "Brown"]

baudrate=9600
# --- Serial / PRIZM ---
port = "/dev/ttyUSB0"   # change if needed
ser = serial.Serial(port, baudrate=9600, timeout=1)


def  initSerComm(baudrate):
    ser= serial.Serial(port, baudrate, timeout=1)
    return ser


def forward():
    return cmdSend(ser, '6')  # expect '6'

def backward():
    return cmdSend(ser, '7')  # expect '7'

def stop():
    return cmdSend(ser, '5')  # expect '5'

def turn_left():
    return cmdSend(ser, '2')  # expect '2'

def turn_right():
    return cmdSend(ser, '3')  # expect '3'


def randomDeg():
    return random.randint(0, 3000)

def randomTurn():
    return random.randint(0, 1)


def cmdSend(ser, cmd):
    # our msg must append a newline symbol, because that symbol is used for controller to check whether the cmd is fully received
    msg = str(cmd) + "\n"
    # encode the msg before sending
    ser.write(msg.encode())
    # originally received msg will end with '\r\n'
    ack_origin = ser.readline()
    # we can skip the last two chars
    # and then decode the msg using utf-8
    ack = ack_origin[:-2].decode("utf-8")
    return ack
#
#def get_color():
#    try:
#        return BP.get_sensor(BP.PORT_1)
#    except brickpi3.SensorError:
#        return 0  
#    
def get_distance():
    ack = cmdSend(ser, 4)
    return ack

def handshake():
    print("*** Press the GREEN button to start the robot ***")
    time.sleep(1.5)
    while True:
        print("--- Sending out handshaking signal ---")
        if cmdSend(ser, 1):
            print("!!! Connected to the robot !!!")
            break
        print("*** Try again ***")
        time.sleep(0.2)

# ======== NEW: ARM CONTROL HELPERS ========

def grab():
    """Close the arm around the object."""
    return cmdSend(ser, 8)   # expect '8'

def release():
    """Open the arm."""
    return cmdSend(ser, 9)   # expect '9'
