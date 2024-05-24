import asyncio
import bisect
import heapq
import json
import traceback
import websockets
from blessed import Terminal

# Initialize blessed terminal
term = Terminal()

prices_dict = {}
MAX_LEN = 60

ENDC = "\033[0m"
GREENC = '\033[92m'
REDC = '\033[91m'


def find_first_positive_index(sorted_list):
    # Create a list of the second values
    second_values = [tup[0] for tup in sorted_list]
    
    # Use bisect_right to find the insertion point for 0 in the list of second values
    index = bisect.bisect_right(second_values, 0)
    
    # Check if the index is within the bounds of the list and if the second value at that index is positive
    if index < len(sorted_list) and sorted_list[index][0] > 0:
        return index
    else:
        # If there's no element greater than 0, return -1 or another sentinel value
        return -1
    
def get_market_short_percentage(price_direction_list):
    i = find_first_positive_index(price_direction_list)
    price_percentage = i * 10 / len(price_direction_list)

    if price_percentage <= 0.3:
        return 0
    elif 9 < price_percentage < 9.7:
        return 9
    return round(price_percentage)

def get_recent_bar_count(lookup_count):
    negative_count = 0
    
    for value_list in prices_dict.values():
        # Check if the list has at least 3 values
        if len(value_list) >= lookup_count:
            last_prices = value_list[-lookup_count:]
            
            # Map the changes: 1 if the price has gone up, -1 if it has gone down
            changes = [1 if last_prices[i] > last_prices[i - 1] else -1 for i in range(1, len(last_prices))]
            
            # Count the number of negative changes
            negative_changes = sum(1 for change in changes if change == -1)
            
            # Check if at least half of the changes are negative
            if negative_changes >= len(changes) / 2:
                negative_count += 1

    price_percentage = negative_count * 10 / len(prices_dict)
    
    if price_percentage <= 0.3:
        return 0
    elif 9 < price_percentage < 9.7:
        return 9
    return round(price_percentage)

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
    for i in range(1, len(prices)):
        weight = i / sum(range(1, len(prices)))  # Weight increases linearly with index
        price_change = abs(prices[i] - prices[i - 1]) / prices[i - 1]  # Absolute price change
        weighted_sum += weight * price_change
        total_weight += weight
    return weighted_sum / total_weight if total_weight != 0 else 0 

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

                            # Get top 5 fastest movers
                            top_5 = get_top_5_fastest_movers()

                            movement_rates  = get_sorted_by_direction()

                            bar_count = get_market_short_percentage(movement_rates) * 2
                            recent_bar_count = get_recent_bar_count(3) * 2

                            print(bar_count)
                            
                            top_up = movement_rates[-5:]
                            top_down = movement_rates[:5]

                            # Clear the terminal
                            print(term.clear)

                            with term.location(0, 0):
                                print(term.bold("Recent market direction:"))
                                bar = " ████████████████████"
                                bar = bar[:recent_bar_count] + GREENC + bar[recent_bar_count:]
                                colored_bar =  REDC + bar + ENDC
                                print(colored_bar)
                                print()

                                print(term.bold("Market direction:"))
                                bar = " ████████████████████"
                                bar = bar[:bar_count] + GREENC + bar[bar_count:]
                                colored_bar =  REDC + bar + ENDC
                                print(colored_bar)
                                print()

                                print(term.bold("Top 5 Fastest Moving:"))
                                for _, (rate_of_change, symbol) in enumerate(top_5):
                                    bar_length = int(rate_of_change * 20)  # Adjust bar length
                                    symbol_colored = term.yellow(symbol)
                                    print(f" {symbol_colored}")
                                print()

                                print(term.bold("Top 5 Winners:"))
                                for _, (rate_of_change, symbol) in reversed(list(enumerate(top_up))):
                                    bar_length = int(rate_of_change * 20)  # Adjust bar length
                                    symbol_colored = term.green(symbol) if rate_of_change >= 0 else term.red(symbol)
                                    print(f" {symbol_colored}")
                                print()

                                print(term.bold("Top 5 Losers:"))
                                for _, (rate_of_change, symbol) in enumerate(top_down):
                                    bar_length = int(rate_of_change * 20)  # Adjust bar length
                                    symbol_colored = term.green(symbol) if rate_of_change >= 0 else term.red(symbol)
                                    print(f" {symbol_colored}")
                                print()

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