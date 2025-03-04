import numpy as np
import pandas as pd

def percentage_difference(old_value, new_value):
    if old_value == 0:
        return 0
    difference = new_value - old_value
    percentage_diff = (difference / old_value)
    return percentage_diff * 100

def append_row(row_data):
    global data
    data = np.vstack([data, row_data])

class Trade:
    def __init__(self, symbol, price, position_amount, entry_time, side_long, entry_reason):
        self.symbol = symbol
        self.entry_price = price
        self.position_amount = position_amount
        self.entry_time = entry_time
        self.side_long = side_long
        self.exit_time = None
        self.exit_price = None
        self.entry_reason = entry_reason

    def check(self, current_price, current_time):
        if self.exit_condition_met(current_price):
            self.exit_time = current_time
            self.exit_price = current_price
            return True
        return False

    def exit_condition_met(self, current_price):
        raise NotImplementedError("Subclass must implement exit_condition_met method")

    def calculate_profit_loss(self):
        if self.exit_price is None:
            return None
        
        if self.position_amount > 0:
            percentage = percentage_difference(self.entry_price, self.exit_price)
            if self.side_long:
                return self.position_amount * percentage / 100
            else:
                return self.position_amount * percentage * -1 / 100
            
        elif self.position_amount < 0:
            return None
        else:
            return 0

class TrailingStopLossTrade(Trade):
    def __init__(self, symbol, price, position_amount, entry_time, side_long, entry_reason, trailing_stop_loss_percentage):
        super().__init__(symbol, price, position_amount, entry_time, side_long, entry_reason)
        self.trailing_stop_loss_percentage = trailing_stop_loss_percentage
        self.highest_price = price

    def exit_condition_met(self, current_price):
        if self.side_long:
            if current_price > self.highest_price:
                self.highest_price = current_price
            elif current_price < self.highest_price - self.highest_price * (self.trailing_stop_loss_percentage / 100):
                return True
        else:
            if current_price < self.highest_price:
                self.highest_price = current_price
            elif current_price > self.highest_price + self.highest_price * (self.trailing_stop_loss_percentage / 100):
                return True
        return False

class ConstantStopLossTrade(Trade):
    def __init__(self, symbol, price, position_amount, entry_time, side_long, entry_reason, stop_loss_price, added_percent):
        super().__init__(symbol, price, position_amount, entry_time, side_long, entry_reason)
        self.stop_loss_price = stop_loss_price
        self.trailing_stop_loss_percentage = added_percent

    def exit_condition_met(self, current_price):
        if self.side_long:
            if current_price <= self.stop_loss_price:
                return True
        else:
            if current_price >= self.stop_loss_price:
                return True
        return False

# Example usage:
if __name__ == "__main__":
    trades = []
    n_columns = 7
    data = np.array([]).reshape(0, n_columns)

    # Create a trade
    trade1 = TrailingStopLossTrade(symbol='AAPL', price=100, position_amount=100, entry_time='2024-05-10 09:30:00', side_long=False, trailing_stop_loss_percentage=1)
    trades.append(trade1)

    # Simulate price movement and check trade exit conditions
    current_price = 110
    current_time = '2024-05-10 10:30:00'
    for trade in trades:
        if trade.check(current_price, current_time):
            profit_loss = trade.calculate_profit_loss()
            data = np.array([]).reshape(0, n_columns)
            print([trade.symbol, trade.entry_time, trade.entry_price, trade.exit_time, trade.exit_price, trade.trailing_stop_loss_percentage, profit_loss])
            append_row(np.array([trade.symbol, trade.entry_time, trade.entry_price, trade.exit_time, trade.exit_price, trade.trailing_stop_loss_percentage, profit_loss]))
            trades.remove(trade)

    df = pd.DataFrame(data, columns=['Symbol', 'Entry Time', 'Entry Price', 'Exit Time', 'Exit Price', 'Trailing Stop Loss', 'Profit/Loss'])
    print(df)
