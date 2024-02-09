import aiohttp
import asyncio
import requests
from requests.exceptions import HTTPError
from time import sleep
from datetime import datetime
from playsound import playsound

BASE_URL = 'https://fapi.binance.com'
RETRACE_THRESHOLD = 35  # Percentage threshold for retracement
MIN_CANDLE_PERCENTAGE = 1
SOUND_FILE = "sounds/wickwickwick.wav"

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
        return 0.0
    open_p, high_p, low_p, close_p = map(float, candlestick[1:5])
    if abs(percentage_diff(high_p, low_p)) < MIN_CANDLE_PERCENTAGE:
        return 0
    total = high_p - low_p
    if close_p > open_p:
        wick = high_p - close_p
    else:
        wick = close_p - low_p
    if not wick:
        return 0
    retracement = wick * 100 / total
    return retracement

def notify(symbol, retracement):
    message = f'{symbol} Retraced {retracement:.2f}%'
    print(message)  # Replace with your notification code
    playsound(SOUND_FILE)

async def track_all_pairs():
    symbols = get_all_usdt_futures_pairs()
    if not symbols:
        return

    while True:
        tasks = [get_candlestick_data(symbol) for symbol in symbols]
        candlesticks_list = await asyncio.gather(*tasks)

        for symbol, candlesticks in zip(symbols, candlesticks_list):
            if len(candlesticks) >= 2:
                retracement = calculate_retracement(candlesticks[0])
                if retracement >= RETRACE_THRESHOLD:
                    notify(symbol, retracement)
                retracement = calculate_retracement(candlesticks[1])
                if retracement >= RETRACE_THRESHOLD:
                    notify(symbol, retracement)

        await asyncio.sleep(20)  # Check every 5 seconds

if __name__ == '__main__':
    asyncio.run(track_all_pairs())
