from utils import assets
import time

print("Loading Users ...")

class User:
    def __init__(self, username, password, name):
        self.username = username
        self.password = password
        self.name = name 
        self.balance = {asset.arr[0][9]: 10000 for asset in assets} # for demo-user, using 10,000 shares as their balance for each asset in the market
        self.collateral = 1000000.00 # for demo-user, 10 lakhs as their purchasing power

    def check_password(self, password):
        return self.password == password

    def update_balance(self, amount):
        if self.balance + amount >= 0:  # Ensure balance doesn't go negative
            self.balance += amount
            return True
        return False


# Simulating a database of users
users = {
    "oic_finance": User(
        "oic_finance",
        "iamuser",
        "Orchid International"
        )
}