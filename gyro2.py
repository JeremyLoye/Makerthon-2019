# Code to read and combine gyroscope and accelerometer data to get
# estimated reading on position

import smbus
import math
import time

from pythonosc import osc_message_builder
from pythonosc import udp_client

# Constants and flag
first_run = True
# Time between each record of data.
CYCLE_TIME = 0.01
# Reliance on past readings and gyroscope data.
WEIGHT = 0.98
# Port to send OSC message to Machine Learning Software on.
PORT = 6448
# Register
power_mgmt_1 = 0x6b
power_mgmt_2 = 0x6c
 
def read_byte(reg):
    return bus.read_byte_data(address, reg)
 
# Read 4-bytes (word-sized) at register
def read_word(reg):
    h = bus.read_byte_data(address, reg)
    l = bus.read_byte_data(address, reg+1)
    value = (h << 8) + l
    return value
 
def read_word_2c(reg):
    val = read_word(reg)
    if (val >= 0x8000):
        return -((65535 - val) + 1)
    else:
        return val

# Implementation of simple complementary filter to combine data
def complementaryFilter(accData, gyroData, pitch, roll):
    # Calculate pitch and roll based on gyroscope
    pitch += (float(gyroData[0])/ 131) * CYCLE_TIME
    roll -= (float(gyroData[1])/131) * CYCLE_TIME
    forceMagnitudeApprox = 0
    for val in accData:
        forceMagnitudeApprox += abs(val)
    if (forceMagnitudeApprox > 8192 and forceMagnitudeApprox < 32768):
        # Calculate pitch based on accelerometer and gyroscope data
        pitchAcc = math.atan2(accData[1], accData[2]) * 180/math.pi
        pitch = pitch * WEIGHT + pitchAcc * (1 - WEIGHT)
        # Calculate roll based on accelerometer and gyroscope data
        rollAcc = math.atan2(accData[0], accData[2]) * 180/math.pi
        roll = roll * WEIGHT + rollAcc * (1 - WEIGHT)
        print "Pitch Acc: ", pitchAcc, " Roll Acc: ", rollAcc
    return [pitch, roll]
 
bus = smbus.SMBus(1) 
address = 0x68       # via i2cdetect
 
# Activate module to write data
bus.write_byte_data(address, power_mgmt_1, 0)

# Starting client for OSC mesage
client = udp_client.SimpleUDPClient('localhost', PORT)

while (True): 
    print("--------")
    
    gyro_xout = read_word_2c(0x43)+ 7 * 131
    gyro_yout = read_word_2c(0x45)
    gyro_zout = read_word_2c(0x47)
    gyroData = [gyro_xout, gyro_yout, gyro_zout]
 
    print "gyro_xout: ", gyro_xout
    print "gyro_yout: ", gyro_yout
    print "gyro_zout: ", gyro_zout
    
    print 
    print "acceleration"
    print "---------------------"
    
    acc_xout = read_word_2c(0x3b)
    acc_yout = read_word_2c(0x3d)
    acc_zout = read_word_2c(0x3f)
    accData = [acc_xout, acc_yout, acc_zout]

    
    print "acc_out: ", ("%6d" % acc_xout), ("%6d" % acc_yout), ("%6d" % acc_zout)
    if first_run:
        # Trust accelerometer if device is first started
        pitch = math.atan2(accData[1], accData[2]) * 180/math.pi
        roll = math.atan2(accData[0], accData[2]) * 180/math.pi
    else:
        pitch, roll = complementaryFilter(accData, gyroData, pitch, roll)
    print "Pitch: ", pitch, " Roll: ", roll
    first_run = False

    # Creating OSC message to send to Machine Learning software
    builder = osc_message_builder.OscMessageBuilder(address="/SYNC")
    builder.add_arg(pitch, builder.ARG_TYPE_FLOAT)
    builder.add_arg(roll, builder.ARG_TYPE_FLOAT)
    msg = builder.build()
    # Send OSC mesage
    client.send_message("/wek/inputs", msg)

    time.sleep(CYCLE_TIME)
