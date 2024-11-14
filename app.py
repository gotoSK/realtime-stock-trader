import random
import time
from datetime import timedelta
from utils import *
from gen_prices import genPrices

from flask import Flask, render_template, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import threading
from sqlalchemy.exc import IntegrityError


# App setups
app = Flask(__name__)

socketio = SocketIO(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)

# Defining the database model
class PriceRow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conID = db.Column(db.String(50), nullable=False, unique=True)
    buyerID = db.Column(db.String(5))
    sellerID = db.Column(db.String(5))
    qty = db.Column(db.Integer)
    rate = db.Column(db.Float)
    buyerName = db.Column(db.String(100))
    sellerName = db.Column(db.String(100))
    symbol = db.Column(db.String(10))
    
    def __repr__(self):
        return f'<Task {self.id}>'
    
    def to_dict(self):
        """Convert SQLAlchemy object to a dictionary."""
        return {
            'id': self.id,
            'conID': self.conID,
            'buyerID': self.buyerID,
            'sellerID': self.sellerID,
            'qty': self.qty,
            'rate': self.rate,
            'buyerName': self.buyerName,
            'sellerName': self.sellerName,
            'symbol': self.symbol
        }


event_start_subThread = threading.Event() # while waiting for main thread to be halted
event_place_LMT = threading.Event() # while LMT order is being placed
lock = threading.Lock()
skip = False

def genConID(OrderNo, rem_mkt_order):
    if rem_mkt_order == False:
        return arr[0][1][:8] + '1' + '0' * (7 - len(str(OrderNo))) + str(OrderNo)
    else:
        placedOrders.append([None])
        return arr[0][1][:8] + '1' + '0' * (7 - len(str(Orders+1))) + str(Orders+1)

def MKT_execute():
    i = MKT_Orders[0]

    if placedOrders[i-1][6] == False:
        placedOrders[i-1][6] = True
        socketio.emit('placed_orders', {'placedOrders': placedOrders})

    if placedOrders[i-1][4] >= sellOB[0][1]:
        if placedOrders[i-1][5] == 'Buy':
            socketio.emit('order_book', {'ltp': sellOB[0][2]})
        else:
            socketio.emit('order_book', {'ltp': buyOB[0][2]})

        # Add data to database
        with app.app_context():
            try:
                global Orders
                rand = random.choice(arr)
                if placedOrders[i-1][5] == 'Buy':
                    if placedOrders[i-1][2] == placedOrders[i-1][4]:
                        new_row = PriceRow(conID=genConID(i, False), buyerID=100, sellerID=rand[3], qty=sellOB[0][1], rate=sellOB[0][2], buyerName='Orchid International', sellerName=rand[8], symbol=arr[0][9])
                    else:
                        new_row = PriceRow(conID=genConID(i, True), buyerID=100, sellerID=rand[3], qty=sellOB[0][1], rate=sellOB[0][2], buyerName='Orchid International', sellerName=rand[8], symbol=arr[0][9])
                        if placedOrders[i-1][4] - sellOB[0][1] != 0:
                            Orders += 1
                else:
                    if placedOrders[i-1][2] == placedOrders[i-1][4]:
                        new_row = PriceRow(conID=genConID(i, False), buyerID=rand[2], sellerID=100, qty=buyOB[0][1], rate=buyOB[0][2], buyerName=rand[7], sellerName='Orchid International', symbol=arr[0][9])
                    else:
                        new_row = PriceRow(conID=genConID(i, True), buyerID=rand[2], sellerID=100, qty=buyOB[0][1], rate=buyOB[0][2], buyerName=rand[7], sellerName='Orchid International', symbol=arr[0][9])
                        if placedOrders[i-1][4] - sellOB[0][1] != 0:
                            Orders += 1
                db.session.add(new_row)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()  # Rollback in case of error
            tranData = PriceRow.query.order_by(PriceRow.id).all()
            tranDataDict = [row.to_dict() for row in tranData] # Convert data to a list of dictionaries
            socketio.emit('floorsheet', {'database': tranDataDict})

        # remaining orders to get filled
        if placedOrders[i-1][4] == 'Buy':
            placedOrders[i-1][4] -= sellOB[0][1]
        else:
            placedOrders[i-1][4] -= buyOB[0][1]
        socketio.emit('placed_orders', {'placedOrders': placedOrders})

        if placedOrders[i-1][4] == 0: # when all qty is filled
            del MKT_Orders[0]

    else:
        bestAskBid = sellOB if placedOrders[i-1][5] == 'Buy' else buyOB
        bestAskBid[0][0] *= int(1 - (placedOrders[i-1][2] / bestAskBid[0][1])) if bestAskBid[0][0] > 1 else bestAskBid[0][0]
        bestAskBid[0][1] -= placedOrders[i-1][4]
        socketio.emit('order_book', {'sellOB': sellOB, 'buyOB': buyOB, 'ltp': bestAskBid[0][2]})

        # Add data to database
        with app.app_context():
            try:
                rand = random.choice(arr)
                if placedOrders[i-1][5] == 'Buy':
                    if placedOrders[i-1][2] == placedOrders[i-1][4]:
                        new_row = PriceRow(conID=genConID(i, False), buyerID=100, sellerID=rand[3], qty=placedOrders[i-1][4], rate=sellOB[0][2], buyerName='Orchid International', sellerName=rand[8], symbol=arr[0][9])
                    else:
                        new_row = PriceRow(conID=genConID(i, True), buyerID=100, sellerID=rand[3], qty=placedOrders[i-1][4], rate=sellOB[0][2], buyerName='Orchid International', sellerName=rand[8], symbol=arr[0][9])
                        if placedOrders[i-1][4] - sellOB[0][1] != 0:
                            Orders += 1
                else:
                    if placedOrders[i-1][2] == placedOrders[i-1][4]:
                        new_row = PriceRow(conID=genConID(i, False), buyerID=rand[2], sellerID=100, qty=placedOrders[i-1][4], rate=buyOB[0][2], buyerName=rand[7], sellerName='Orchid International', symbol=arr[0][9])
                    else:
                        new_row = PriceRow(conID=genConID(i, True), buyerID=rand[2], sellerID=100, qty=placedOrders[i-1][4], rate=buyOB[0][2], buyerName=rand[7], sellerName='Orchid International', symbol=arr[0][9])
                        if placedOrders[i-1][4] - sellOB[0][1] != 0:
                            Orders += 1
                db.session.add(new_row)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()  # Rollback in case of error
            tranData = PriceRow.query.order_by(PriceRow.id).all()
            tranDataDict = [row.to_dict() for row in tranData] # Convert data to a list of dictionaries
            socketio.emit('floorsheet', {'database': tranDataDict})

        # all qty filled
        placedOrders[i-1][4] = 0
        socketio.emit('placed_orders', {'placedOrders': placedOrders})
        del MKT_Orders[0]

def orderMatch_sim():
    def genOB(rate):
        # top bid & ask prices in order book
        bidPrices = []; askPrices = []
        bidPrices = genPrices(rate, 'bids')
        askPrices = genPrices(rate, 'asks')

        # generating asks order book
        for i in range(0, TOP_BIDSASKS_NO): # filling each row in order book
            sellOB.append([0, 0, askPrices[i]]) # initializing row data: [orders, qty, price]
            brokers = [] # collects all the brokers in the list for that particular price
            if(i == 0):
                idx = 0
                while(idx < len(arr) and arr[idx][5] == sellOB[i][2]):
                    idx += 1
                idx -= 1
                if(idx != -1):
                    for x in queue:
                        count = -1
                        for y in x:
                            if(sellOB[i][2] == y[5]):
                                sellOB[i][1] += y[4]
                                brokers.append(y[3])
                                count += 1
                                if(count == idx):
                                    break
                        if(sellOB[i][1] != 0):
                            break
            else:
                for x in queue:
                    for y in x:
                        if(sellOB[i][2] == y[5]): # to find orders data realted to current price in queue
                            sellOB[i][1] += y[4] # fetching qty and adding
                            brokers.append(y[3]) # append all brokers
                        else:
                            break
                    if(sellOB[i][1] != 0):
                        break
            if(len(brokers) == 0):
                sellOB[i][1] = int(random.triangular(10, 1300, 200)) # random qty between 10-1300, mostly being of 100-300
                sellOB[i][0] = int(random.triangular(1, 20, 7)) # random qty between 1-20, mostly being around 7
            else:
                sellOB[i][0] = len(remove_duplicates(brokers)) # total orders   
        # for row in reversed(sellOB):
        #     print(row)
        # print()
        
        # generating bids order book
        for i in range(0, TOP_BIDSASKS_NO):
            buyOB.append([0, 0, bidPrices[i]])
            brokers = []
            for x in queue:
                for y in x:
                    if(buyOB[i][2] == y[5]):
                        buyOB[i][1] += y[4]
                        brokers.append(y[2])
                    else:
                        break
                if(buyOB[i][1] != 0):
                    break
            if(len(brokers) == 0):
                buyOB[i][1] = int(random.triangular(10, 1300, 200))
                buyOB[i][0] = int(random.triangular(1, 20, 7))
            else:
                buyOB[i][0] = len(remove_duplicates(brokers))
        # for row in buyOB:
        #     print(row)

        if mkt_ex_mode == False:
            socketio.emit('order_book', {'sellOB': sellOB, 'buyOB': buyOB, 'ltp': arr[0][5]})
            # Add data to database
            for x in queue:
                if x[0][5] == arr[0][5]:
                    with app.app_context():
                        try:
                            new_row = PriceRow(conID=x[0][1], buyerID=x[0][2], sellerID=x[0][3], qty=x[0][4], rate=x[0][5], buyerName=x[0][7], sellerName=x[0][8], symbol=x[0][9])
                            db.session.add(new_row)
                            db.session.commit()
                        except IntegrityError:
                            db.session.rollback()  # Rollback in case of error
                            
                        tranData = PriceRow.query.order_by(PriceRow.id).all()
                        tranDataDict = [row.to_dict() for row in tranData] # Convert data to a list of dictionaries
                        socketio.emit('floorsheet', {'database': tranDataDict})
        else:
            socketio.emit('order_book', {'sellOB': sellOB, 'buyOB': buyOB})


    def linear_price():
        if len(arr) > 1:
            price_diff = round(arr[1][5] - arr[0][5], 1)
            if abs(price_diff) > 0.3:
                global mkt_ex_mode

                factor = abs(price_diff)*10 - 1
                i = 1 if price_diff>0 else -1

                time_diff = arr[1][6] - arr[0][6]
                time_diff = time_diff.total_seconds()

                def next_rate(i):
                    return round(arr[0][5] + 0.1*i, 1)
                
                while True:
                    flag = 0
                    while next_rate(i) != arr[1][5]:
                        for price in prices:
                            if price == next_rate(i):
                                i = i+1 if i>0 else i-1
                                flag = 1
                                factor += 1
                                break
                        if(flag == 0):
                            break
                        flag = 0
                    if next_rate(i) == arr[1][5]:
                        break
                    sellOB.clear()
                    buyOB.clear()
                    # print("--------------------------------")
                    genOB(next_rate(i))
                    i = i+1 if i>0 else i-1

                    if len(MKT_Orders) != 0:
                        MKT_execute()
                        mkt_ex_mode = True

                    else:
                        if subThreads > 0:
                            time.sleep(time_diff/factor)
                        else:
                            if time_diff/factor > 2:
                                time.sleep(time_diff/factor)
                            else:
                                time.sleep(2)
                mkt_ex_mode = False

    def matchOrder(i):
        if buyOB[0][2] == sellOB[0][2]: # when top bid & ask price match
            for idx, x in enumerate(queue):
                for y in x:
                    if buyOB[0][2] == y[5]:
                        # if a LMT order matches
                        if y[1][8:9] == '1':
                            global placedOrders
                            for indx in range(9, 16):
                                if y[1][indx] != '0':
                                    placedOrders[int(y[1][indx:])-1][4] = 0
                                    socketio.emit('placed_orders', {'placedOrders': placedOrders})

                        # if i >= 150:
                        linear_price()

                        del queue[idx][0] # delete first order of that price
                        if len(queue[idx]) == 0: # if orders in that price is empty
                            del queue[idx] # delete that element of queue
                            del prices[idx] # delete that particular price from prices list
                        del arr[0]
                        return
                    else:
                        break


    i = 1 # S.N. of matched order
    while len(arr) != 0:
        # print("##################################")
        genOB(arr[0][5])
        matchOrder(i)

        sellOB.clear()
        buyOB.clear()
        i += 1
        if subThreads > 0:
            event_start_subThread.set()
            event_place_LMT.wait()

            event_start_subThread.clear()
            event_place_LMT.clear()
    print("end")


def LMT_place(Rate, Qty, OrderNo, type):
    global skip
    OrderData = []
    
    def genTime(idx):
        if idx-1 < 0:
            return arr[idx][6] + timedelta(microseconds=-1)
        if idx+1 == len(arr):
            return arr[idx][6] + timedelta(microseconds=1)
        else:
            return arr[idx-1][6] + (arr[idx][6] - arr[idx-1][6]) / 2

    def write_orderData():
        nonlocal OrderData
        rand = random.choice(arr)
        if type == 'Buy':
            OrderData = ['', genConID(OrderNo, False), 100, rand[3], Qty, Rate, genTime(idx), 'Orchid International', rand[8], arr[0][9]]
        else:
            OrderData = ['', genConID(OrderNo, False), rand[2], 100, Qty, Rate, genTime(idx), rand[7], 'Orchid International', arr[0][9]]

    def in_the_end():
        global subThreads, skip, placedOrders
        placedOrders[OrderNo-1][6] = True
        socketio.emit('placed_orders', {'placedOrders': placedOrders})
        subThreads -= 1
        if subThreads == 0:
            event_place_LMT.set()
            skip = False
        else:
            skip = True

    with lock: # following threads (placed orders) wait before the first thread is completely placed in data structures
        if skip == False:
            event_start_subThread.wait() # wait for main-thread to check if orders have matched before overwriting the new order to the data structure
        
        compare = (lambda x, y: x < y) if type == 'Buy' else (lambda x, y: x > y)
        for idx, next in enumerate(arr):
            if compare(next[5], Rate):
                write_orderData()
                arr.insert(idx, OrderData)
                encounter = False
                for i, price in enumerate(prices):
                    if price == Rate:
                        queue[i].insert(0, OrderData)
                        encounter = True
                        break
                    elif price > Rate:
                        prices.insert(i, Rate)
                        queue.insert(i, [OrderData])
                        encounter = True
                        break
                if encounter == False:
                    prices.append(Rate)
                    queue.append([OrderData])
                in_the_end()
                return

            elif next[5] == Rate:
                count = 0
                while True:
                    if arr[idx+1][5] == Rate:
                        idx += 1
                        count += 1
                    else:
                        write_orderData()
                        arr.insert(idx+1, OrderData)
                        for i, price in enumerate(prices):
                            if price == Rate:
                                write_orderData()
                                queue[i].insert(count+1, OrderData)
                                break
                        break
                in_the_end()
                return

        if type == 'Buy':
            write_orderData()
            arr.append(OrderData)
            prices.insert(0, Rate)
            queue.insert(0, [OrderData])
        else:
            write_orderData()
            arr.append(OrderData)
            prices.append(Rate)
            queue.append([OrderData])
        in_the_end()


# Home page
@app.route("/")
def index():
    return render_template("index.html", prevClose=prevClose)

# Handle the form submission (AJAX)
@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        global Orders, placedOrders, subThreads
        
        Rate = float(request.form.get('rate'))
        Qty = int(request.form.get('qty'))
        action = request.form.get('action')  # Get whether it's a buy or sell order
        Orders += 1

        if Rate == 0: # market execution
            placedOrders.append([Orders, arr[0][9], Qty, 'MKT', Qty, action, False])
            MKT_Orders.append(Orders)
        else: # normal limit order
            placedOrders.append([Orders, arr[0][9], Qty, Rate, Qty, action, False])
            subThreads += 1
            threading.Thread(target=LMT_place, args=(Rate, Qty, Orders, action)).start() # run process in background
        socketio.emit('placed_orders', {'placedOrders': placedOrders})

        return "Order successfully placed", 200
    except Exception as e:
        print(f"Error: {str(e)}")  # Debugging line for error
        return str(e), 400


# Runner & debugger
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    threading.Thread(target=orderMatch_sim).start()
    socketio.run(app, debug=True)