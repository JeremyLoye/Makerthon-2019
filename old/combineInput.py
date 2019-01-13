import readGyro
import time
import sys
import serial
import socket

from pythonosc import osc_message_builder
from pythonosc import udp_client
from threading import Thread
from multiprocessing import Array, Value
from subprocess import call

# Port to send OSC message to Machine Learning Software on.
PORT = 6448
# Time between each record of data.
CYCLE_TIME = 0.05
# Starting client for OSC mesage
client = udp_client.SimpleUDPClient('localhost', PORT)

def readBluetoothInput(ser):
    return ser.readline().decode("utf-8").strip()

def sendOSCMsg(path, msg):
    global client
    # Creating OSC message to send to Machine Learning software
    builder = osc_message_builder.OscMessageBuilder(address="/SYNC")
    for value in msg:
        builder.add_arg(value, builder.ARG_TYPE_FLOAT)
        print(value)
    msg = builder.build()
    client.send_message(path, msg)

# Calls readGyro method to generate pitch, roll and yaw data at fixed intervals.
def runRead(client, thread):
    time.sleep(3)
    first_run = True
    pitch, roll,yaw, dummyValue = [0,0,0,0]
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
        thread.join(timeout=CYCLE_TIME)
        if not thread.is_alive():
            break

def readBluetooth(ser):
    while True:
        text = readBluetoothInput(ser)
        if text == "1":
            break

def listenSocket(socket, ser):
    while True:
        data = socket.recv(1024).decode('utf-8')
        print(data)
        text = data.strip()
        userInput = readBluetoothInput(ser)
        if userInput == "1":
            break
        if text:
            ser.write(text.encode('utf-8'))
            break

def openBluetoothPort():
    call(["sudo rfcomm listen hci0"], shell = True)

def openOutput():
    call(["python3 /home/pi/output.py"], shell = True)

def waitingConnection():
    while True:
        try:
            bluetoothSer = serial.Serial('/dev/rfcomm0')
            return bluetoothSer
        except IOError:
            time.sleep(0.5)
    
def main():
    time.sleep(5)
    bluetoothPort_Thread = Thread(target=openBluetoothPort, args=())
    bluetoothPort_Thread.start()
    output_thread = Thread(target=openOutput, args=())
    output_thread.start()
    connSock = socket.socket()
    connSock.bind(("localhost", 8080))
    connSock.listen(1)
    client_socket, address = connSock.accept()
    bluetoothSer = waitingConnection()
    bluetoothSer.write(b"Connected Device; Files Running.\n")
    print("Bluetooth serial running, input and outfile connected.")
    while True:
        bluetoothSer.write(b"Please Input Command: \n")
        bluetoothSer.write(b"1: Record Data; 2: Train Data; 3: Save Data\n 4: Run Programme; 5: Power Options\n")
        print("Next command input")
        cmd = readBluetoothInput(bluetoothSer)
        print(cmd)
        if cmd == "1":
            # Start recording
            while True:
                bluetoothSer.write(b"Select Direction to record:\n")
                bluetoothSer.write(b"1: Centre; 2: Left; 3: Right\n 4: Up; 5: Down; 6: to quit\n")
                print("Direction input")
                direction = readBluetoothInput(bluetoothSer)
                if direction.isdigit():
                    direction = float(direction)
                    if direction >=1 and direction <=5:
                        sendOSCMsg("/wekinator/control/outputs", [direction])
                        sendOSCMsg("/wekinator/control/startRecording", [])
                        input_thread = Thread(target=readBluetooth, args=(bluetoothSer, ))
                        input_thread.start()
                        bluetoothSer.write(b"Recording Started. Press '1' to stop.\n")
                        runRead(client, input_thread)
                        sendOSCMsg("/wekinator/control/stopRecording", [])
                        print("Done Recording")
                    elif direction == 6.0:
                        break
        elif cmd =="2":
            # Train data
            sendOSCMsg("/wekinator/control/train", [])
            bluetoothSer.write(b"Training Data...\n")
            time.sleep(2)
        elif cmd=="3":
            # Save Current Model
            call(["xdotool windowactivate --sync \"$(xdotool search --name gestureLearn)\" key Alt+f Down Down Return"], shell=True)
        elif cmd == "4":
            # Run programme
            sendOSCMsg("/wekinator/control/startRunning", [])
            run_thread = Thread(target=listenSocket, args=(client_socket,bluetoothSer))
            run_thread.start()
            bluetoothSer.write(b"Run Started. Press '1' to stop.\n")
            runRead(client, run_thread)
            sendOSCMsg("/wekinator/control/stopRunning", [])
        elif cmd == "5":
            bluetoothSer.write(b'1: Reboot; 2: Shutdown\n')
            text = readBluetoothInput(bluetoothSer)
            if text == "1":
                call(["sudo reboot"], shell=True)
            elif text == "2":
                # Shutdown
                call(["sudo shutdown -h now"], shell=True)
            elif text=="3":
                break


if __name__ == '__main__':
    main()
