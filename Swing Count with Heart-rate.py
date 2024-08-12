import asyncio
from bleak import BleakScanner, BleakClient
import math
from datetime import datetime
import os
from art import text2art
# import pyautogui
import csv

HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"  
ACCELEROMETER_UUID = "fb005c82-02e7-f387-1cad-8acd2d8df0c8"
ACCELEROMETER_UUID_WRITE = "fb005c81-02e7-f387-1cad-8acd2d8df0c8"
ACC_WRITE = bytearray([0x02, 0x02, 0x00, 0x01, 0xC8, 0x00, 0x01, 0x01, 0x10, 0x00, 0x02, 0x01, 0x08, 0x00])
HEART_RATE_HANDLE = ''
ACCELEROMETER_HANDLE = ''
STANDING_POS = [-60, 205, -971]
HINGE_POS = [-56, -624, -792]

TIMER_START = datetime.now()
HEART = 0
ACC = [0, 0, 0]
POS = 'Stand'
TIMESTAMP = 0
FILENAME = ''
LAST_POS = 'Stand'
SWING_COUNT = 0

def create_file_with_current_date():
    global FILENAME, SWING_COUNT
    current_date = datetime.now().strftime("%Y-%m-%d")
    FILENAME = 'data/' + current_date + ".txt"
    if os.path.exists(FILENAME):
        print("File already exists for today's date.")
        with open(FILENAME, 'r') as file:
            reader = csv.reader(file)
            last_line = None
            for line in reader:
                last_line = line
            if last_line:
                SWING_COUNT = int(last_line[-1])
            return
        
    with open(FILENAME, "w") as file:
        # file.write("This file was created on " + current_date)
        file.write("")
    
    print("File", FILENAME, "has been created.")

def append_to_file(text):
    with open(FILENAME, 'a') as file:
        file.write(text)

def decode_heart_rate(data):
    flags = data[0]
    if flags & 1:
        heart_rate = int.from_bytes(data[1:3], byteorder='little')
    else:
        heart_rate = data[1]
    return heart_rate

def decode_accelerometer(data):
    global TIMESTAMP
    if data[0] == 0x02:
        TIMESTAMP = int.from_bytes(bytearray(data[1:9]), byteorder="little", signed=False)
        frame_type = data[9]
        resolution = (frame_type + 1) * 8
        step = math.ceil(resolution / 8.0)
        samples = data[10:] 
        offset = 0
        while offset < len(samples):
            x = int.from_bytes(bytearray(data[offset : offset + step]), byteorder="little", signed=True,)
            offset += step
            y = int.from_bytes(bytearray(data[offset : offset + step]), byteorder="little", signed=True,)
            offset += step
            z = int.from_bytes(bytearray(data[offset : offset + step]), byteorder="little", signed=True,)
            offset += step
        return {'x': x, 'y': y, 'z': z}

def position(accelerometer_data):
    current_pos = [accelerometer_data['x'], accelerometer_data['y'], accelerometer_data['z']]
    dist_from_stand = abs(math.dist(current_pos, STANDING_POS))
    dist_from_hinge = abs(math.dist(current_pos, HINGE_POS))
    if dist_from_hinge * 2 < dist_from_stand:
        return 'Hinge'
    if dist_from_stand * 2 < dist_from_hinge:
        return 'Stand'
    return 'Neither'

def count_swings():
    global LAST_POS, SWING_COUNT
    if POS != LAST_POS and POS in ['Stand', 'Hinge']:
            LAST_POS = POS
            if POS == 'Stand':
                SWING_COUNT += 1

def callback(sender, data):
    global HEART, ACC, POS, CONT, BEGIN_WORKOUT, TIMER_START, LAST_POS, SWING_COUNT
    if sender.handle == HEART_RATE_HANDLE:
        HEART = decode_heart_rate(data)
    elif sender.handle == ACCELEROMETER_HANDLE:
        accelerometer_data = decode_accelerometer(data)
        ACC = f"\tx: {int(accelerometer_data['x'])}\n\ty: {int(accelerometer_data['y'])}\n\tz: {int(accelerometer_data['z'])}\n"
        POS = position(accelerometer_data)
        count_swings()
        timer = datetime.now() - TIMER_START
        minutes, seconds = divmod(timer.total_seconds(), 60)
        formatted_time = '{:02}:{:02}'.format(int(minutes), int(seconds))
        print('\r')
        # print(f"BPM: {HEART}\nSwings: {SWING_COUNT}\nTimer: {formatted_time}")
        print(text2art(f"BPM: {HEART}\nSwings: {SWING_COUNT}\nTimer: {formatted_time}"))
        print("\x1b[2J\x1b[H", end="")
        append_to_file(f"{TIMESTAMP},{int(accelerometer_data['x'])},{int(accelerometer_data['y'])},{int(accelerometer_data['z'])},{HEART},{SWING_COUNT}\n")

async def run_bleak():
    global HEART_RATE_HANDLE
    global ACCELEROMETER_HANDLE
    print("Scanning for devices...")
    devices = await BleakScanner.discover()
    for device in devices:
        if device.name and "Polar" in device.name:
            async with BleakClient(device.address) as client:
                print(f"Connecting to {device.name}")
                if await client.connect():
                    print(f"Connected to {device.name}, start receiving data.")
                    HEART_RATE_HANDLE = client.services.get_characteristic(HEART_RATE_UUID).handle
                    ACCELEROMETER_HANDLE = client.services.get_characteristic(ACCELEROMETER_UUID).handle
                    await client.start_notify(HEART_RATE_UUID, callback)
                    await client.write_gatt_char(ACCELEROMETER_UUID_WRITE, ACC_WRITE, response=True)
                    await client.start_notify(ACCELEROMETER_UUID, callback)
                    await asyncio.get_event_loop().run_in_executor(None, input, "Press Enter to stop...\n")
                    await client.stop_notify(HEART_RATE_UUID)
                    await client.stop_notify(ACCELEROMETER_UUID)
                else:
                    print(f"Failed to connect to {device.name}")
                break
    print("Disconnected.")


create_file_with_current_date()
loop = asyncio.get_event_loop()
loop.run_until_complete(run_bleak())
