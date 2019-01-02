# Code to read Gyroscope once and convert readings to
# appropriate estimated pitch and roll values.

import smbus
import math

# Constants and flag
first_run = True
# Time between each record of data.
CYCLE_TIME = 0.01
# Reliance on past readings and gyroscope data.
WEIGHT = 0.98
# Register
power_mgmt_1 = 0x6b
power_mgmt_2 = 0x6c

address = 0


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

# Simple filter implemented to get account for noise of accelerometer
# with gyroscope to get more accurate readings.
def complementaryFilter(accData, gyroData, pitch, roll):
    pitch += (float(gyroData[0]) / 131) * CYCLE_TIME
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
        print("Pitch Acc: ", pitchAcc, " Roll Acc: ", rollAcc)
    return [pitch, roll]


bus = smbus.SMBus(1)

# Call function to run one round of gyroscope read with calculation of
# estimated data.
def run(add, offsetX, offsetY, offsetZ, pitch, roll):
    global address
    global first_run
    # Activate module to write data
    bus.write_byte_data(add, power_mgmt_1, 0)
    address = add
    print("--------")

    gyro_xout = read_word_2c(0x43) + offsetX
    gyro_yout = read_word_2c(0x45) + offsetY
    gyro_zout = read_word_2c(0x47) + offsetZ
    gyroData = [gyro_xout, gyro_yout, gyro_zout]

    print("gyro_xout: ", gyro_xout)
    print("gyro_yout: ", gyro_yout)
    print("gyro_zout: ", gyro_zout)

    acc_xout = read_word_2c(0x3b)
    acc_yout = read_word_2c(0x3d)
    acc_zout = read_word_2c(0x3f)
    accData = [acc_xout, acc_yout, acc_zout]

    print("acc_out: ", ("%6d" % acc_xout),
          ("%6d" % acc_yout), ("%6d" % acc_zout))
    if first_run:
        pitch = math.atan2(accData[1], accData[2]) * 180/math.pi
        roll = math.atan2(accData[0], accData[2]) * 180/math.pi
    else:
        pitch, roll = complementaryFilter(accData, gyroData, pitch, roll)
    print("Pitch: ", pitch, " Roll: ", roll)
    first_run = False
    return [pitch, roll]
