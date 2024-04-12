#!/usr/bin/env python3
import random
import string
import argparse
import serial
import re
from enum import Enum

class Modes(Enum):
    DETERMINISTIC = 1
    RANDOM = 2
    STATIC = 3

ap = argparse.ArgumentParser()
ap.add_argument("-v", "--verbose", help="Enables verbose output", action="store_true")
ap.add_argument("-g", "--generate-only", help="Only generates an IMEI rather than setting it", action="store_true")
modes = ap.add_mutually_exclusive_group()
modes.add_argument("-d", "--deterministic", help="Switches IMEI generation to deterministic mode", action="store_true")
modes.add_argument("-s", "--static", help="Sets user-defined IMEI", action="store")
modes.add_argument("-r", "--random", help="Sets random IMEI", action="store_true")

imei_length = 14 # without validation digit

imei_prefix = [
    "352073", # Samsung
    "352074", # iPhone
    "352075", # Sony
    "352076", # LG
    "352077", # Nokia
    "352078", # Huawei
    "352079", # Xiaomi
    "352080" # OnePlus
]

verbose = False
mode = None

TTY = '/dev/ttyUSB3'
BAUDRATE = 9600
TIMEOUT = 3

def luhn_check(imei):
    sum = 0
    num_digits = len(imei)
    oddeven = num_digits & 1

    for i in range(0, num_digits):
        digit = int(imei[i])
        if not ((i & 1) ^ oddeven):
            digit *= 2
        if digit > 9:
            digit -= 9
        sum += digit

    return (10 - (sum % 10)) % 10

def generate_imei(imei_prefix, imsi_d=None):
    if mode == Modes.DETERMINISTIC:
        random.seed(imsi_d)

    tac = random.choice(imei_prefix)
    imei = tac + "".join(random.sample(string.digits, imei_length - len(tac)))

    validation_digit = luhn_check(imei)
    imei = str(imei) + str(validation_digit)

    return imei

def validate_imei(imei):
    if len(imei) != 15:
        return False

    validation_digit = int(imei[-1])
    imei_verify = imei[0:14]

    validation_digit_verify = luhn_check(imei_verify)

    return validation_digit == validation_digit_verify

def get_imsi():
    with serial.Serial(TTY, BAUDRATE, timeout=TIMEOUT, exclusive=True) as ser:
        ser.write(b'AT+CIMI\r')
        output = ser.read(64)
        imsi_d = re.findall(b'[0-9]{15}', output)
        return b"".join(imsi_d)

def set_imei(imei):
    with serial.Serial(TTY, BAUDRATE, timeout=TIMEOUT, exclusive=True) as ser:
        cmd = b'AT+EGMR=1,7,\"'+imei.encode()+b'\"\r'
        ser.write(cmd)
        output = ser.read(64)

    new_imei = get_imei()
    return new_imei == imei.encode()

def get_imei():
    with serial.Serial(TTY, BAUDRATE, timeout=TIMEOUT, exclusive=True) as ser:
        ser.write(b'AT+GSN\r')
        output = ser.read(64)
        imei_d = re.findall(b'[0-9]{15}', output)
        return b"".join(imei_d)

if __name__ == '__main__':
    args = ap.parse_args()
    if args.verbose:
        verbose = args.verbose
    if args.deterministic:
        mode = Modes.DETERMINISTIC
        imsi_d = get_imsi()
    if args.random:
        mode = Modes.RANDOM
    if args.static is not None:
        mode = Modes.STATIC
        static_imei = args.static

    if mode == Modes.STATIC:
        if validate_imei(static_imei):
            set_imei(static_imei)
        else:
            exit(-1)
    else:
        imei = generate_imei(imei_prefix, imsi_d)
        if not args.generate_only:
            if not set_imei(imei):
                exit(-1)

    exit(0)
