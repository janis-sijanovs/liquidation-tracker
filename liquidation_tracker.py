import asyncio
import csv
from datetime import datetime, timedelta
import json
import os
import time
import traceback
from playsound import playsound
import websockets

COOLDOWN_TIME = 2
cooldown_start = time.time()

TRESHOLD = 10000

MINI_TRESHOLD = 3000

EXCLUDED = ["BTC", "SOL", "ETH"]

SOUND_FILE = "sounds/liquidation.wav"

SOUND_NORMAL = "sounds/alarm_normal.mp3"
SOUND_HIGHER = "sounds/alarm_higher.mp3"
SOUND_MAX = "sounds/alarm_max.mp3"
SOUND_NEW_SYMBOL = "sounds/symbol.mp3"

SYMBOL_LIST_FILE = "symbol_list.csv"

def read_symbol_list_csv():
    if os.path.exists(SYMBOL_LIST_FILE):
        with open(SYMBOL_LIST_FILE, 'r', newline='') as file:
            reader = csv.reader(file)
            symbol_list = [symbol for row in reader for symbol in row]
        print(symbol_list)
        return symbol_list
    else:
        return []
    
def write_symbol_list_csv(symbol_list):
    with open(SYMBOL_LIST_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows([symbol_list])

symbol_list = read_symbol_list_csv()

def play_sound(sound_file):
    global cooldown_start
    current_time = time.time()

    if current_time - cooldown_start <= COOLDOWN_TIME:
        return 0
    
    cooldown_start = current_time

    try:
        playsound(sound_file)
    except Exception as e:
        print("sound error")
        print()


def calc_liq_amount(liq_data):
    price = float(liq_data["p"])
    quantity = float(liq_data["q"])

    liq_amount = price * quantity

    return liq_amount


def percentage_difference(old_value, new_value):
    if old_value == 0:
        return 0
    difference = new_value - old_value
    percentage_diff = (difference / old_value)
    return percentage_diff * 100

# Function to get the color code based on the direction
def get_direction_color(direction):
    if direction.upper() == "LONG":
        return '\033[92m'  # Green color for LONG
    elif direction.upper() == "SHORT":
        return '\033[91m'  # Red color for SHORT
    else:
        return '\033[0m'   # Default color for other cases

# Function to get the color code based on the percentage value
def get_percentage_color(percent_liq):
    if percent_liq > 1:
        return '\033[93m'  # Orange color for percentage greater than 1
    elif percent_liq > 2.5:
        return '\033[91m'  # Orange color for percentage greater than 1
    else:
        return '\033[0m'   # Default color for other cases
    
# Function to get the color code based on the prefix of data['s']
def get_data_color(s):
    if s[:3] in EXCLUDED:
        return '\033[90m'  # Gray color for excluded prefixes
    else:
        return '\033[35m'   # Default color for other cases
    
def get_liq_amount_color(liq_amount, s_prefix):
    if liq_amount >= TRESHOLD and s_prefix not in EXCLUDED:
        return '\033[94m'  # Blue color for liq_amount greater than or equal to TRESHOLD and not in EXCLUDED
    else:
        return '\033[0m'   # Default color for other cases



async def ws_connect(endpoint):
    reconnect_attempts = 0

    while True:
        try:
            async with websockets.connect(endpoint) as ws:
                print(f"Connected to {endpoint} successfully!")

                # Subscribe to depth stream for each symbol
                depth_stream_name = f"!forceOrder@arr"
                subscribe_msg = {
                    "method": "SUBSCRIBE",
                    "params": [depth_stream_name],
                    "id": 1
                }
                await ws.send(json.dumps(subscribe_msg))

                while True:
                    message = await ws.recv()
                    data = json.loads(message)

                    if "stream" in data:
                        stream_name = data["stream"]
                        if "@arr" in stream_name:
                            data = data["data"]["o"]

                            open_price = float(data["ap"])
                            liq_price = float(data["p"])

                            percent_liq = percentage_difference(open_price, liq_price)

                            liq_amount = calc_liq_amount(data)

                            ts = data["T"]

                            seconds = ts // 1000
                            milliseconds = ts % 1000
                            dt_base = datetime.fromtimestamp(seconds)
                            dt = dt_base + timedelta(milliseconds=milliseconds)

                            if data['s'][-4:] == "USDT" and data['s'] not in symbol_list:
                                symbol_list.append(data['s'])
                                print(f"NEW SYMBOL {data['s']}!")
                                print()
                                play_sound(SOUND_NEW_SYMBOL)

                            if liq_amount >= TRESHOLD or (liq_amount >= MINI_TRESHOLD and data['s'][:3] not in EXCLUDED):
                                dt = dt.replace(microsecond=0)

                                direction = "SHORT" if data['S'] == "BUY" else "LONG"
                                colored_output = f"{dt} {get_data_color(data['s'])}{data['s']} {get_direction_color(direction)}{direction}\033[0m liquidated {get_liq_amount_color(liq_amount, data['s'][:3])}${int(liq_amount)}\033[0m {get_percentage_color(percent_liq)}{abs(round(percent_liq, 2))}%\033[0m"

                                print(colored_output)
                                print()

                                if data['s'][:3] not in EXCLUDED:

                                    if liq_amount >= 100000:
                                        play_sound(SOUND_MAX)

                                    elif liq_amount >= 50000:
                                        play_sound(SOUND_HIGHER)

                                    elif liq_amount >= 21000:
                                        play_sound(SOUND_NORMAL)
                                        
                                    elif liq_amount >= TRESHOLD or percent_liq > 2.5:
                                        play_sound(SOUND_FILE)

        except Exception as e:
            print(f"Connection error: {e}")
            traceback.print_exc()
            reconnect_attempts += 1
            if True:
                print(f"Reconnecting... (Attempt {reconnect_attempts})")
                await asyncio.sleep(10)  # Wait for 5 seconds before attempting to reconnect
            else:
                print("Maximum reconnection attempts reached. Exiting...")
                break

if __name__ == "__main__":

    endpoint = "wss://fstream.binance.com/stream?streams=!forceOrder@arr"

    try:
        asyncio.get_event_loop().run_until_complete(ws_connect(endpoint))
    except KeyboardInterrupt:
        # Catch a KeyboardInterrupt (e.g., Ctrl+C) to stop the loop gracefully
        print("Received KeyboardInterrupt, stopping the loop...")
    finally:
        write_symbol_list_csv(symbol_list)
        print("Data fetching disrupted!")