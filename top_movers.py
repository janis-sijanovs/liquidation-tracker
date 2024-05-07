import asyncio
import heapq
import json
import traceback
import websockets
from blessed import Terminal

# Initialize blessed terminal
term = Terminal()

prices_dict = {}
MAX_LEN = 60

def update_mark_price(symbol, price):
    if symbol in prices_dict:
        prices_dict[symbol].append(float(price))

        if len(prices_dict[symbol]) > MAX_LEN:
            prices_dict[symbol].pop(0)
    else:
        prices_dict[symbol] = [float(price)]

def calculate_rate_of_change(symbol):
    prices = prices_dict[symbol]
    if len(prices) < 2:
        return 0  # If there's only one price, we can't calculate the change
    
    # Calculate weighted average rate of change
    weighted_sum = 0
    total_weight = 0
    for i, price in enumerate(prices):
        weight = (i + 1) / sum(range(1, len(prices) + 1))  # Weight increases linearly with index
        if i > 0:
            weighted_sum += weight * (price - prices[i - 1]) / prices[i - 1]  # Weighted price change
            total_weight += weight
    return weighted_sum / total_weight if total_weight != 0 else 0  # Calculate weighted average


def get_top_5_fastest_movers():
    movers = []
    for symbol in prices_dict:
        rate_of_change = calculate_rate_of_change(symbol)
        heapq.heappush(movers, (rate_of_change, symbol))
        if len(movers) > 5:
            heapq.heappop(movers)
    return sorted(movers, reverse=True)


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

                            # Get top 5 fastest movers
                            top_5 = get_top_5_fastest_movers()

                            # Clear the terminal
                            print(term.clear)

                            with term.location(0, 0):
                                print(term.bold("Top 5 Fastest Moving Coins:"))
                                for _, (rate_of_change, symbol) in enumerate(top_5):
                                    bar_length = int(rate_of_change * 20)  # Adjust bar length
                                    symbol_colored = term.green(symbol) if rate_of_change >= 0 else term.red(symbol)
                                    print(f" {symbol_colored}")

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
        print("Data fetching disrupted!")