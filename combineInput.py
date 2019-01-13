# Code to implement full functionality of bluetooth and button input to control
# gesture-to-speech programme

import readGyro
import time
import sys
import serial
import socket
import RPi.GPIO as GPIO

from pythonosc import osc_message_builder
from pythonosc import udp_client
from threading import Thread
from multiprocessing import Array, Value
from subprocess import call
#from xdo import Xdo

# Port to send OSC message to Machine Learning Software on.
PORT = 6448
# Time between each record of data.
CYCLE_TIME = 0.05
# Starting client for OSC mesage
time.sleep(5)
client = udp_client.SimpleUDPClient('localhost', PORT)
#xdo = Xdo()
buttonPressed = False

ser = None

# Read input from bluetooth connection
def readBluetoothInput(ser):
    try:
        return ser.readline().decode("utf-8").strip()
    except NameError:
        return 0

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
def run(client_socket, bluetoothSer):
    # Run programme
    sendOSCMsg("/wekinator/control/startRunning", [])
    run_thread = Thread(target=listenSocket, args=(
        client_socket, bluetoothSer))
    run_thread.start()
    manualStop_thread = Thread(target=readBluetooth, args=(bluetoothSer))
    manualStop_thread.start()
    bluetoothSer.write(b"Run Started. Press '1' to stop.\n")
    runRead(client, [run_thread, manualStop_thread], 0)
    sendOSCMsg("/wekinator/control/stopRunning", [])

# Calls readGyro method to generate pitch, roll and yaw data at fixed intervals.
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
        else:
            yaw_diff = yaw - neutral_yaw
        values = [pitch, roll, yaw_diff]
        print("Pitch, roll, yaw: ", values)
        sendOSCMsg("/wek/inputs", values)
        for thread in threads:
            thread.join(timeout=CYCLE_TIME)
            if not thread.is_alive():
                return

# Seperate thread to listen for input from bluetooth to stop recording.
def readBluetooth(ser):
    while True:
        text = readBluetoothInput(ser)
        if text == "1":
            break

# Listens on port of TCP connection established with output.py for control messages.
def listenSocket(socket, ser):
    while True:
        data = socket.recv(1024).decode('utf-8')
        print(data)
        text = data.strip()
        if text:
            ser.write(text.encode('utf-8'))
            break

def openBluetoothPort():
    call(["sudo rfcomm listen hci0"], shell=True)

# Opens output.py file
def openOutput():
    call(["python3 /home/pi/output.py"], shell=True)

# Try to establish connection with any bluetooth connected device.
def waitingConnection():
    global ser
    while True:
        try:
            ser = serial.Serial('/dev/rfcomm0')
        except IOError:
            time.sleep(0.5)

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

# Attempt to write to connected bluetooth device.
def bluetoothWrite(ser, string):
    try:
        ser.write(string)
    except NameError:
        print("No connection")

def main():
    global buttonPressed, ser
    # Start listening on bluetooth port
    bluetoothPort_Thread = Thread(target=openBluetoothPort, args=())
    bluetoothPort_Thread.setDaemon(True)
    bluetoothPort_Thread.start()
    # Open output.py file
    output_thread = Thread(target=openOutput, args=())
    output_thread.setDaemon(True)
    output_thread.start()
    # Establish TCP connection with output file.
    connSock = socket.socket()
    connSock.bind(("localhost", 8080))
    connSock.listen(1)
    client_socket, address = connSock.accept()
    # Set up button
    buttonSetup()
    # Attempt to bluetooth connection with phone.
    connectionThread = Thread(target=waitingConnection, args=())
    connectionThread.setDaemon(True)
    connectionThread.start()
    bluetoothWrite(ser, b"Connected Device; Files Running.\n")
    print("Bluetooth serial running, input and outfile connected.")
    while True:
        # Check if bluetooth connection is established
        connectionThread.join(timeout=0.01)
        bluetoothWrite(ser, b"Please Input Command: \n")
        bluetoothWrite(ser, b"1: Record Data; 2: Train Data; 3: Save Data\n 4: Run Programme; 5: Power Options\n")
        print("Next command input")
        cmd = readBluetoothInput(ser)
        # Button press takes priority over bluetooth input
        if buttonPressed or cmd == "4":
            run(client_socket, ser)
        elif cmd == "1":
            # Start recording
            while True:
                bluetoothWrite(ser, b"Select Direction to record:\n")
                bluetoothWrite(ser, b"1: Centre; 2: Left; 3: Right\n 4: Up; 5: Down; 6: to quit\n")
                print("Direction input")
                direction = readBluetoothInput(ser)
                if direction.isdigit():
                    direction = float(direction)
                    if direction >= 1 and direction <= 5:
                        sendOSCMsg("/wekinator/control/outputs", [direction])
                        sendOSCMsg("/wekinator/control/startRecording", [])
                        # Listen for bluetooth input to stop recording
                        input_thread = Thread(target=readBluetooth, args=(ser, ))
                        input_thread.start()
                        bluetoothWrite(ser, b"Recording Started. Press '1' to stop.\n")
                        runRead(client, input_thread, 1)
                        sendOSCMsg("/wekinator/control/stopRecording", [])
                        print("Done Recording")
                    elif direction == 6.0:
                        break
        elif cmd == "2":
            # Train data
            sendOSCMsg("/wekinator/control/train", [])
            bluetoothWrite(ser, b"Training Data...\n")
            time.sleep(2)
        elif cmd == "3":
            # Save Wekinator project with automatic button press sequence.
            '''window, = xdo.search_windows(winname=b'gestureLearn')
            bluetoothSer.write(window.encode('utf-8'))
            xdo.activate_window(window)
            #xdo.focus_window(window)
            xdo.wait_for_window_focus(window, 1)
            window = xdo.get_focused_window()
            xdo.send_keysequence_window(window, b'Alt+f')
            xdo.send_keysequence_window(window, b'Down')
            xdo.send_keysequence_window(window, b'Down')
            xdo.send_keysequence_window(window, b'Return')'''
        elif cmd == "5":
            #power options
            bluetoothWrite(ser, b"1: Reboot; 2: Shutdown\n")
            text = readBluetoothInput(ser)
            if text == "1":
                # reboot
                call(["sudo reboot"], shell=True)
                connSock.close()
            elif text == "2":
                # Shutdown
                call(["sudo shutdown -h now"], shell=True)
                connSock.close()
        time.sleep(0.05)


if __name__ == '__main__':
    main()
