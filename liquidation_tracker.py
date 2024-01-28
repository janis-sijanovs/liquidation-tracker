import asyncio
from datetime import datetime, timedelta
import json
import traceback
from playsound import playsound
import websockets

TRESHOLD = 10000

SOUND_FILE = "sounds/liquidation.wav"

def calc_liq_amount(liq_data):
    price = float(liq_data["p"])
    quantity = float(liq_data["q"])

    liq_amount = price * quantity

    return liq_amount


def percentage_difference(old_value, new_value):
    difference = new_value - old_value
    percentage_diff = (difference / old_value)
    return percentage_diff * 100


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

                            if liq_amount > TRESHOLD:
                                dt = dt.replace(microsecond=0)

                                if data['S'] == "BUY":
                                    print(f"{dt} {data['s']} SHORT liquidated ${int(liq_amount)} {abs(round(percent_liq, 2))}%")
                                else:
                                    print(f"{dt} {data['s']} LONG liquidated ${int(liq_amount)} {abs(round(percent_liq, 2))}%")
                                print()
                                playsound(SOUND_FILE)

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
        print("Data fetching disrupted!")