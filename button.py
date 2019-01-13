# Code to make gesture-to-speech programme run on button push alone.

import readGyro
import time
import socket
import serial
import RPi.GPIO as GPIO

from pythonosc import osc_message_builder
from pythonosc import udp_client
from subprocess import call
from threading import Thread

# Port to send OSC message to Machine Learning Software on.
PORT = 6448
# Time between each record of data.
CYCLE_TIME = 0.05
# Starting client for OSC mesage
time.sleep(5)
client = udp_client.SimpleUDPClient('localhost', PORT)
buttonPressed = False
ser = None

# Send OSC message to Wekinator.
def sendOSCMsg(path, msg):
    global client
    # Creating OSC message to send to Machine Learning software
    builder = osc_message_builder.OscMessageBuilder(address="/SYNC")
    for value in msg:
        builder.add_arg(value, builder.ARG_TYPE_FLOAT)
        print(value)
    msg = builder.build()
    client.send_message(path, msg)

# Function to start running Wekinator and generating input data from gyroscope.
def run(client_socket):
    # Run programme
    sendOSCMsg("/wekinator/control/startRunning", [])
    run_thread = Thread(target=listenSocket, args=(client_socket))
    run_thread.start()
    runRead(client, [run_thread], 0)
    sendOSCMsg("/wekinator/control/stopRunning", [])

# Start generating gyroscope data.
def runRead(client, threads, op):
    global buttonPressed
    if op == 0:
        time.sleep(3)
    first_run = True
    pitch, roll, yaw, dummyValue = [0, 0, 0, 0]
    while True:
        pitch, roll = readGyro.run(0x68, 0, 0, 400, pitch, roll)
        dummyValue, yaw = readGyro.run(0x69, 700, -80, 0, dummyValue, yaw)
        # Yaw values differ depending on which direction user is facing. The 0 point
        # is set to the direction the user faces when the method is first called.
        if first_run:
            neutral_yaw = yaw
            yaw_diff = 0
            first_run = False
        else:
            yaw_diff = yaw - neutral_yaw
        values = [pitch, roll, yaw_diff]
        print("Pitch, roll, yaw: ", values)
        sendOSCMsg("/wek/inputs", values)
        for thread in threads:
            thread.join(timeout=CYCLE_TIME)
            if not thread.is_alive():
                return

# Listens on port of TCP connection established with output.py for control messages.
def listenSocket(socket):
    while True:
        data = socket.recv(1024).decode('utf-8')
        print(data)
        text = data.strip()
        if text:
            break

# Opens output.py file
def openOutput():
    call(["python3 /home/pi/output.py"], shell=True)

# Action when button is pressed.
def button_callback(channel):
    global buttonPressed
    buttonPressed = True

# Setting up button with its matching GPIO pin.
def buttonSetup():
    GPIO.setwarnings(False)  # Ignore warning for now
    GPIO.setmode(GPIO.BOARD)  # Use physical pin numbering
    # Set pin 10 to be an input pin and set initial value to be pulled low (off)
    GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    # Setup event on pin 10 rising edge
    GPIO.add_event_detect(10, GPIO.RISING, callback=button_callback)

def main():
    global buttonPressed
    output_thread = Thread(target=openOutput, args=())
    output_thread.setDaemon(True)
    output_thread.start()
    connSock = socket.socket()
    connSock.bind(("localhost", 8080))
    connSock.listen(1)
    client_socket, address = connSock.accept()
    buttonSetup()
    while True:
        if buttonPressed:
            buttonPressed = False
            run(client_socket)
        time.sleep(0.05)

if __name__ == '__main__':
    main()