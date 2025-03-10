from utils import assets
import time

print("Loading Users ...")

class User:
    def __init__(self, username, password, name, is_admin, uid):
        self.username = username
        self.password = password
        self.name = name 
        self.balance = {asset.arr[0][9]: 100000 for asset in assets}  # for demo-user, using 1,00,000 shares as their balance for each asset in the market
        self.collateral = 1000000.00  # for demo-user, 10 lakhs as their purchasing power
        self.is_admin = is_admin
        self.uid = uid

    def check_password(self, password):
        return self.password == password

def get_user(uid):
    for user in users:
        if users[user].uid == uid:
            return user


# Simulating a database of users
users = {
    "oic_finance": User(
        "oic_finance",
        "iamuser",
        "Orchid International",
        False,
        "101"
        ),

    "sugam_karki": User(
        "sugam_karki",
        "iamuser",
        "Sugam Karki",
        False,
        "102"
        ),

    "anish_tamang": User(
        "anish_tamang",
        "iamuser",
        "Anish Tamang",
        False,
        "103"
        ),

    "parag_niraula": User(
        "parag_niraula",
        "iamuser",
        "Parag Niraula",
        False,
        "104"
        ),
        
    "admin": User(
        "admin",
        "iamadmin",
        "Administrator",
        True,
        "100"
        )
}