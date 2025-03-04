import asyncio
import random
import heapq
import json
import time
import traceback
import websockets
import numpy as np
import pandas as pd
from trade import TrailingStopLossTrade, ConstantStopLossTrade

prices_dict = {}
MAX_LEN = 60

trades = []
n_columns = 8
data = np.array([]).reshape(0, n_columns)

def get_stop_loss(symbol, side_long, added_percentage):
    if side_long:
        lowest_price = min(prices_dict[symbol])
        return lowest_price - lowest_price * added_percentage / 100
    else:
        highest_price = max(prices_dict[symbol])
        return highest_price + highest_price * added_percentage / 100

def append_row(row_data):
    global data
    data = np.vstack([data, row_data])

def get_trailing_percentage():
    trailing = 0.8
    return trailing

def update_mark_price(symbol, price):
    if symbol in prices_dict:
        prices_dict[symbol].append(float(price))

        if len(prices_dict[symbol]) > MAX_LEN:
            prices_dict[symbol].pop(0)
    else:
        prices_dict[symbol] = [float(price)]

def calculate_direction_of_change(symbol):
    prices = prices_dict[symbol]
    if len(prices) < 2:
        return 0  # If there's only one price, we can't calculate the change
    
    # Calculate weighted average rate of change
    weighted_sum = 0
    total_weight = 0
    for i in range(1, len(prices)):
        weight = i / sum(range(1, len(prices)))  # Weight increases linearly with index
        price_change = (prices[i] - prices[i - 1]) / prices[i - 1]  # Price change
        weighted_sum += weight * price_change
        total_weight += weight
    return weighted_sum / total_weight if total_weight != 0 else 0

def calculate_rate_of_change(symbol):
    prices = prices_dict[symbol]
    if len(prices) < 2:
        return 0  # If there's only one price, we can't calculate the change
    
    # Calculate weighted average rate of change
    weighted_sum = 0
    total_weight = 0
    for i in range(1, len(prices)):
        weight = i / sum(range(1, len(prices)))  # Weight increases linearly with index
        price_change = abs(prices[i] - prices[i - 1]) / prices[i - 1]  # Absolute price change
        weighted_sum += weight * price_change
        total_weight += weight
    return weighted_sum / total_weight if total_weight != 0 else 0 


def get_top_5_fastest_movers():
    movers = []
    for symbol in prices_dict:
        rate_of_change = calculate_rate_of_change(symbol)
        heapq.heappush(movers, (rate_of_change, symbol))
        if len(movers) > 5:
            heapq.heappop(movers)
    return sorted(movers, reverse=True)

def get_sorted_by_direction():
    movers = []
    for symbol in prices_dict:
        direction = calculate_direction_of_change(symbol)
        heapq.heappush(movers, (direction, symbol))
    return sorted(movers)

async def ws_connect(endpoint):
    reconnect_attempts = 0

    while True:
        try:
            async with websockets.connect(endpoint) as ws:
                print(f"Connected to {endpoint} successfully!")

                # Subscribe to depth stream for each symbol
                depth_stream_name = f"!markPrice@arr"
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
                        if "!markPrice@arr" in stream_name:
                            data = data["data"]
                            for symbol_data in data:
                                symbol = symbol_data["s"]
                                price = float(symbol_data["p"])

                                if symbol[-4:] == "USDT":
                                    update_mark_price(symbol, price)

                            
                            if len(prices_dict["BTCUSDT"]) >= MAX_LEN:
                                current_time = time.time()

                                for trade in trades:
                                    if trade.check(prices_dict[trade.symbol][-1], current_time):
                                        profit_loss = trade.calculate_profit_loss()
                                        append_row(np.array([trade.entry_reason, trade.symbol, trade.entry_time, trade.entry_price, trade.exit_time, trade.exit_price, trade.trailing_stop_loss_percentage, profit_loss]))
                                        trades.remove(trade)


                                # # Get top 5 fastest movers
                                # top_5 = get_top_5_fastest_movers()

                                # for (rate_of_change, symbol) in top_5:
                                #     reason = False

                                #     if prices_dict[symbol][-1] > prices_dict[symbol][-20] and prices_dict[symbol][-20] > prices_dict[symbol][-40] and prices_dict[symbol][-40] > prices_dict[symbol][0]:
                                #         reason = "3 Bullish top"
                                #         long = False
                                #     elif prices_dict[symbol][-1] > prices_dict[symbol][-20] and prices_dict[symbol][-20] > prices_dict[symbol][-40]:
                                #         reason = "2 Bullish top"
                                #         long = False
                                #     elif prices_dict[symbol][-1] < prices_dict[symbol][-20] and prices_dict[symbol][-20] < prices_dict[symbol][-40] and prices_dict[symbol][-40] < prices_dict[symbol][0]:
                                #         reason = "3 Bearish top"
                                #         long = True
                                #     elif prices_dict[symbol][-1] < prices_dict[symbol][-20] and prices_dict[symbol][-20] < prices_dict[symbol][-40]:
                                #         reason = "2 Bearish top"
                                #         long = True

                                #     if reason:    
                                #         trade = TrailingStopLossTrade(symbol, prices_dict[symbol][-1], 100, current_time, long, reason, get_trailing_percentage())
                                #         trades.append(trade)
                                        
                                # Get top 5 fastest movers
                                movement_rates  = get_sorted_by_direction()

                                top_up = movement_rates[-5:]
                                top_down = movement_rates[:5]

                                for (rate_of_change, symbol) in top_up:
                                    reason = False

                                    if prices_dict[symbol][-1] > prices_dict[symbol][-20] and prices_dict[symbol][-20] > prices_dict[symbol][-40] and prices_dict[symbol][-40] > prices_dict[symbol][0]:
                                        reason = "3 Bullish bull"
                                        long = True
                                    elif prices_dict[symbol][-1] > prices_dict[symbol][-20] and prices_dict[symbol][-20] > prices_dict[symbol][-40]:
                                        reason = "2 Bullish bull"
                                        long = True

                                    if reason:    
                                        # if random.randint(1,2) == 2:
                                        #     stop_loss_extra_percent_options = [0, 0, 0, 0.5, 0,5, 1, 1, 1.5, 2]
                                        #     stop_loss_extra_percent = random.choice(stop_loss_extra_percent_options)
                                        #     reason += " const"
                                        #     trade = ConstantStopLossTrade(symbol, prices_dict[symbol][-1], 100, current_time, long, reason, get_stop_loss(symbol, long, stop_loss_extra_percent), stop_loss_extra_percent)
                                        # else:
                                        trade = TrailingStopLossTrade(symbol, prices_dict[symbol][-1], 100, current_time, long, reason, get_trailing_percentage())
                                        trades.append(trade)

                                for (rate_of_change, symbol) in top_down:
                                    reason = False

                                    if prices_dict[symbol][-1] < prices_dict[symbol][-20] and prices_dict[symbol][-20] < prices_dict[symbol][-40] and prices_dict[symbol][-40] < prices_dict[symbol][0]:
                                        reason = "3 Bearish bear"
                                        long = False
                                    elif prices_dict[symbol][-1] < prices_dict[symbol][-20] and prices_dict[symbol][-20] < prices_dict[symbol][-40]:
                                        reason = "2 Bearish bear"
                                        long = False

                                    if reason:    
                                        # if random.randint(1,2) == 2:
                                        #     stop_loss_extra_percent_options = [0, 0, 0, 0.5, 0,5, 1, 1, 1.5, 2]
                                        #     stop_loss_extra_percent = random.choice(stop_loss_extra_percent_options)
                                        #     reason += " const"
                                        #     trade = ConstantStopLossTrade(symbol, prices_dict[symbol][-1], 100, current_time, long, reason, get_stop_loss(symbol, long, stop_loss_extra_percent), stop_loss_extra_percent)
                                        # else:
                                        trade = TrailingStopLossTrade(symbol, prices_dict[symbol][-1], 100, current_time, long, reason, get_trailing_percentage())
                                        trades.append(trade)


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

    endpoint = "wss://fstream.binance.com/stream?streams=!markPrice@arr"

    try:
        asyncio.get_event_loop().run_until_complete(ws_connect(endpoint))
    except KeyboardInterrupt:
        # Catch a KeyboardInterrupt (e.g., Ctrl+C) to stop the loop gracefully
        print("Received KeyboardInterrupt, stopping the loop...")
    finally:
        df = pd.DataFrame(data, columns=['Entry Reason', 'Symbol', 'Entry Time', 'Entry Price', 'Exit Time', 'Exit Price', 'Trailing Stop Loss', 'Profit/Loss'])
        df.to_csv('trade_testing_data.csv', index=False)
        print("Data fetching disrupted!")