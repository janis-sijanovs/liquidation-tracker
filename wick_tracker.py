import aiohttp
import asyncio
import requests
from requests.exceptions import HTTPError
from time import sleep
from datetime import datetime, timedelta
from playsound import playsound

BASE_URL = 'https://fapi.binance.com'
RETRACE_THRESHOLD = 35  # Percentage threshold for retracement
MIN_CANDLE_PERCENTAGE = 1
LARGE_CANDLE_PERCENT = 3
SOUND_FILE = "sounds/wickwickwick.wav"
LARGE_SOUND_FILE = "sounds/largelarge.wav"

message_history = {}
large_history = {}

def percentage_diff(high, low):
    return (high - low) * 100 / high

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
    retracement, direction, candle_percent = calculate_retracement(candle)
    if candle_percent > LARGE_CANDLE_PERCENT:
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
        if large_history[symbol][0] == dt and large_history[symbol][1] >= candle_percent:
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
    playsound(LARGE_SOUND_FILE)

    if symbol not in large_history.keys() or dt > large_history[symbol][0]:
        large_history[symbol] = [dt, candle_percent]

def notify(symbol, dt, retracement, direction, candle_percent):
    try:
        if message_history[symbol] == dt:
            return 0
    except KeyError:
        pass
    
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
    playsound(SOUND_FILE)

    
    if symbol not in message_history.keys() or dt > message_history[symbol]:
        message_history[symbol] = dt

async def track_all_pairs():
    symbols = get_all_usdt_futures_pairs()
    if not symbols:
        return

    while True:
        tasks = [get_candlestick_data(symbol) for symbol in symbols]
        candlesticks_list = await asyncio.gather(*tasks)

        for symbol, candlesticks in zip(symbols, candlesticks_list):
            if len(candlesticks) >= 2:
                for candle in candlesticks:
                    check_candle(symbol, candle)

        await asyncio.sleep(20)  # Check every 5 seconds

if __name__ == '__main__':
    asyncio.run(track_all_pairs())
