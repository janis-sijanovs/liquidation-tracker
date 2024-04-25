import json
from datetime import datetime

FORMAT_STRING = "%d.%m.%Y %H:%M"
DATA_FILE = "trendline_data.json"

def read_trendline_txt():
    with open(DATA_FILE, 'r') as file:
        trendline_dict = json.load(file)
    return trendline_dict

trendline_dict = read_trendline_txt()

def main():
    try:
        while True:
            add_trendline()
    finally:
        with open(DATA_FILE, 'w') as file:
            json.dump(trendline_dict, file)
        print("Script stopped.")

def get_new_trendline_data():
    symbol = input("Symbol name: ")
    t1 = input("First time point (20.12.2012 12:00): ")
    p1 = input("First price: ")
    t2 = input("Second time point (20.12.2012 12:00): ")
    p2 = input("Second price: ")

    try:
        p1 = float(p1)
        p2 = float(p2)
    except ValueError:
        print("Invalid price")

    try:
        t1 = datetime.strptime(t1, FORMAT_STRING).timestamp()
        t2 = datetime.strptime(t2, FORMAT_STRING).timestamp()
    except ValueError:
        print("Incorrect datetime format")
        return False
    
    return symbol, [t1, p1, t2, p2, True]

def add_trendline():
    input_data = get_new_trendline_data()

    if not input_data:
        return False
    
    symbol, data = input_data

    if symbol in trendline_dict.keys():
        trendline_dict[symbol].append(data)
    else:
        trendline_dict[symbol] = [data]

if __name__ == "__main__":
    main()