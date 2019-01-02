import readGyro
import time

from pythonosc import osc_message_builder
from pythonosc import udp_client

# Port to send OSC message to Machine Learning Software on.
PORT = 6448
# Time between each record of data.
CYCLE_TIME = 0.2

# Starting client for OSC mesage
client = udp_client.SimpleUDPClient('localhost', PORT)
pitch, roll,yaw, dummyValue = [0,0,0,0]

while(True):
    pitch, roll = readGyro.run(0x68, 0, 0, 400, pitch, roll)
    dummyValue, yaw = readGyro.run(0x69, 700, -80, 0, dummyValue, yaw)
    values = [pitch, roll, yaw]
    print("Ptich, roll, yaw: ", values)
    # Creating OSC message to send to Machine Learning software
    builder = osc_message_builder.OscMessageBuilder(address="/SYNC")
    builder.add_arg(pitch, builder.ARG_TYPE_FLOAT)
    builder.add_arg(roll, builder.ARG_TYPE_FLOAT)
    builder.add_arg(yaw, builder.ARG_TYPE_FLOAT)
    msg = builder.build()
    # Send OSC mesage
    client.send_message("/wek/inputs", msg)
    time.sleep(CYCLE_TIME)
