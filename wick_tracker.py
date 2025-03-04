import time
import json
import aiohttp
import asyncio
import requests
from requests.exceptions import HTTPError
from datetime import datetime, timedelta
from playsound import playsound

FORMAT_STRING = "%d.%m.%Y %H:%M"
TRENDLINE_DATA_FILE = "trendline_data.json"

def read_trendline_file():
    with open(TRENDLINE_DATA_FILE, 'r') as file:
        trendline_dict = json.load(file)
    return trendline_dict

trendline_dict = read_trendline_file()

BASE_URL = 'https://fapi.binance.com'
RETRACE_THRESHOLD = 35  # Percentage threshold for retracement
MIN_CANDLE_PERCENTAGE = 1
LARGE_CANDLE_PERCENT = 3
TRENDLINE_ALERT_PERCENTAGE = 1.5
TRENDLINE_ACTIVATE_PERCENTAGE = 2.5
SOUND_FILE = "sounds/wickwickwick.wav"
LARGE_SOUND_FILE = "sounds/liqliqliqliqliq.wav"
TRENDLINE_SOUND_FILE = "sounds/trendline.mp3"

EXCEPTIONS = []

message_history = {}
large_history = {}

COOLDOWN_TIME = 2
cooldown_start = time.time()

def percentage_diff(high, low):
    return (high - low) * 100 / high

def play_sound(sound_file):

    if sound_file == SOUND_FILE:
        return 0

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

def interpolate_price(t, t1, p1, t2, p2):
    return p1 + (p2 - p1) * ((t - t1) / (t2 - t1))

def check_trendlines(symbol, close_price):
    if not symbol in trendline_dict.keys():
        return False
    
    ts = time.time()
    
    trendlines = trendline_dict[symbol]
    for i, trendline in enumerate(trendlines):
        t1, p1, t2, p2, active = trendline

        p = interpolate_price(ts, t1, p1, t2, p2)
        percentage = abs(percentage_diff(close_price, p))
        if active and percentage <= TRENDLINE_ALERT_PERCENTAGE:

            dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            message = f'{dt} \033[35m{symbol}\033[0m\033[94m Close to trendline!\033[0m'
            print(message)
            print()
            play_sound(TRENDLINE_SOUND_FILE)

            trendline_dict[symbol][i][4] = False

        elif not active and percentage >= TRENDLINE_ACTIVATE_PERCENTAGE:
            trendline_dict[symbol][i][4] = True

def get_all_usdt_futures_pairs():
    try:
        response = requests.get(f'{BASE_URL}/fapi/v1/exchangeInfo')
        response.raise_for_status()
        exchange_info = response.json()
        return [symbol['symbol'] for symbol in exchange_info['symbols'] if symbol['quoteAsset'] == 'USDT' and 'PERPETUAL' in symbol['contractType']]
    except HTTPError as e:
        print(f'Error getting exchange information: {e}')
        return None

async def get_candlestick_data(symbol, interval='1m'):
    try:
        params = {'symbol': symbol, 'interval': interval, 'limit': 2}
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{BASE_URL}/fapi/v1/klines', params=params) as response:
                response.raise_for_status()
                return await response.json()
    except HTTPError as e:
        print(f'Error getting candlestick data for {symbol}: {e}')
        return None

def calculate_retracement(candlestick):
    if not len(candlestick):
        return 0, "", 0
    
    open_p, high_p, low_p, close_p = map(float, candlestick[1:5])
    candle_percent = abs(percentage_diff(high_p, low_p))
    
    total = high_p - low_p

    if close_p > open_p:
        upper_shadow = high_p - close_p
        lower_shadow = open_p - low_p
        wick = max(upper_shadow, lower_shadow)
    else:
        upper_shadow = close_p - low_p
        lower_shadow = high_p - open_p
        wick = max(upper_shadow, lower_shadow)

    if not wick:
        return 0, "", candle_percent
    
    retracement = wick * 100 / total
    direction = "DOWN" if upper_shadow > lower_shadow else "UP"
    return retracement, direction, candle_percent


def check_candle(symbol, candle):
    check_trendlines(symbol, float(candle[4]))
    retracement, direction, candle_percent = calculate_retracement(candle)
    if abs(candle_percent) > LARGE_CANDLE_PERCENT:
        ts = candle[0]

        seconds = ts // 1000
        milliseconds = ts % 1000
        dt_base = datetime.fromtimestamp(seconds)
        dt = dt_base + timedelta(milliseconds=milliseconds)
        dt = dt.replace(microsecond=0)

        notify_large(symbol, dt, candle_percent)

    if retracement >= RETRACE_THRESHOLD and candle_percent > MIN_CANDLE_PERCENTAGE:
        ts = candle[0]

        seconds = ts // 1000
        milliseconds = ts % 1000
        dt_base = datetime.fromtimestamp(seconds)
        dt = dt_base + timedelta(milliseconds=milliseconds)
        dt = dt.replace(microsecond=0)
        
        notify(symbol, dt, retracement, direction, candle_percent)

def notify_large(symbol, dt, candle_percent):
    try:
        if large_history[symbol][0] == dt:
            return 0
    except KeyError:
        pass
    
    if candle_percent >2.5:
        color_percent = '\033[94m'  # ANSI escape code for green color
    else:
        color_percent = ''  # Default color

    # Your original message
        
    message = f'{dt} \033[35m{symbol}\033[0m Large \033[94m{candle_percent:.2f}%\033[0m Candle'
    print(message)  # Replace with your notification code
    print()
    play_sound(LARGE_SOUND_FILE)

    if symbol not in large_history.keys() or dt > large_history[symbol][0]:
        large_history[symbol] = [dt, candle_percent]

def notify(symbol, dt, retracement, direction, candle_percent):
    try:
        if message_history[symbol] == dt:
            return 0
    except KeyError:
        pass

    if symbol in EXCEPTIONS:
        return 0
    
    if direction == 'UP':
        color_code = '\033[92m'  # ANSI escape code for green color
    elif direction == 'DOWN':
        color_code = '\033[91m'  # ANSI escape code for red color
    else:
        color_code = ''  # Default color
    
    if candle_percent >2.5:
        color_percent = '\033[94m'  # ANSI escape code for green color
    else:
        color_percent = ''  # Default color

    # Your original message
        
    message = f'{dt} \033[35m{symbol}\033[0m {color_code}{direction}\033[0m {retracement:.2f}% from {color_percent}{candle_percent:.2f}% \033[0m'
    print(message)  # Replace with your notification code
    print()
    # play_sound(SOUND_FILE)

    
    if symbol not in message_history.keys() or dt > message_history[symbol]:
        message_history[symbol] = dt

async def track_all_pairs():
    symbols = get_all_usdt_futures_pairs()
    for symbol in symbols:
        if symbol[:3] == "XEM":
            symbols.remove(symbol)

    if not symbols:
        return False

    while True:
        tasks = [get_candlestick_data(symbol) for symbol in symbols]
        candlesticks_list = await asyncio.gather(*tasks)

        for symbol, candlesticks in zip(symbols, candlesticks_list):
            if len(candlesticks) >= 2:
                for candle in candlesticks:
                    check_candle(symbol, candle)

        await asyncio.sleep(15)  # Check every 5 seconds

def run_infinite():
    try:
        asyncio.run(track_all_pairs())
    except KeyboardInterrupt:
        print("Interrupted")
        exit(0)
    except Exception as e:
        print("error")
        run_infinite()

if __name__ == '__main__':
    run_infinite()
