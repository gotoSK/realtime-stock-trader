from utils import *
from gen_prices import genPrices
from user import users, get_user
from market_making import maker
from order_del import del_orders

import random
import time
from datetime import timedelta, datetime

from flask import Flask, render_template, redirect, request, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from sqlalchemy.exc import IntegrityError


# App setups
print("Configuring App & DB setups ...")
app = Flask(__name__)
socketio = SocketIO(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".db"  # database file name: database<date_time of creation>.db
db = SQLAlchemy(app)

app.secret_key = 'your_secret_key'  # Change this to a secure random string


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


event_firstEmit = threading.Event()
lock_start = threading.Lock()
lock_db = threading.Lock()
lock_emit = threading.Lock()

event_place_order_inc_order_no = threading.Event()
event_place_order_inc_order_no.set()
event_mkt_exec_inc_order_no = threading.Event()
event_mkt_exec_inc_order_no.set()

finish = False  # wrap up order matching simulation immediately
barrier = threading.Barrier(len(assets))
event_terminate = False  # True if user orders are already deleted or in process to be deleted
lock_del = threading.Lock()
finished = False  # trading session ended


def genConID(rem_mkt_order, OrderNo):
    global placedOrders

    if rem_mkt_order == True:
        placedOrders.append([])

    return datecode + '1' + '0' * (7 - len(str(OrderNo))) + str(OrderNo)

def MKT_execute(obj):
    global placedOrders
    i = MKT_Orders[0] # grab order id of this order

    # Order ready to be filled
    if placedOrders[i-1][6] == False:
        placedOrders[i-1][6] = True
        socketio.emit('placed_orders', {'placedOrders': placedOrders})

    # When the best bid/ask qty < mkt order's qty
    if (placedOrders[i-1][4] >= obj.sellOB[0][1] and placedOrders[i-1][5] == 'Buy') or (placedOrders[i-1][4] >= obj.buyOB[0][1] and placedOrders[i-1][5] == 'Sell'):
        # Update LTP
        if placedOrders[i-1][5] == 'Buy':
            socketio.emit('order_book', {'ltp': obj.sellOB[0][2], 'sym': placedOrders[i-1][1]})
            # deduct collateral
            socketio.emit('deduct_req', {'amt': obj.sellOB[0][2] * obj.sellOB[0][1], 'uname': placedOrders[i-1][7]})
        else:
            socketio.emit('order_book', {'ltp': obj.buyOB[0][2], 'sym': placedOrders[i-1][1]})

        # Add data to database
        with app.app_context():
            try:
                global Orders
                rand = maker(obj.arr)
                if placedOrders[i-1][5] == 'Buy':
                    if placedOrders[i-1][2] == placedOrders[i-1][4]:
                        new_row = PriceRow(conID=genConID(False, i), buyerID=users[placedOrders[i-1][7]].uid, sellerID=rand[3], qty=obj.sellOB[0][1], rate=obj.sellOB[0][2], buyerName=users[placedOrders[i-1][7]].name, sellerName=rand[8], symbol=obj.arr[0][9])
                    else:
                        event_place_order_inc_order_no.wait()
                        event_mkt_exec_inc_order_no.clear()
                        Orders += 1
                        new_row = PriceRow(conID=genConID(True, Orders), buyerID=users[placedOrders[i-1][7]].uid, sellerID=rand[3], qty=obj.sellOB[0][1], rate=obj.sellOB[0][2], buyerName=users[placedOrders[i-1][7]].name, sellerName=rand[8], symbol=obj.arr[0][9])
                        event_mkt_exec_inc_order_no.set()
                else:
                    if placedOrders[i-1][2] == placedOrders[i-1][4]:
                        new_row = PriceRow(conID=genConID(False, i), buyerID=rand[2], sellerID=users[placedOrders[i-1][7]].uid, qty=obj.buyOB[0][1], rate=obj.buyOB[0][2], buyerName=rand[7], sellerName=users[placedOrders[i-1][7]].name, symbol=obj.arr[0][9])
                    else:
                        event_place_order_inc_order_no.wait()
                        event_mkt_exec_inc_order_no.clear()
                        Orders += 1
                        new_row = PriceRow(conID=genConID(True, Orders), buyerID=rand[2], sellerID=users[placedOrders[i-1][7]].uid, qty=obj.buyOB[0][1], rate=obj.buyOB[0][2], buyerName=rand[7], sellerName=users[placedOrders[i-1][7]].name, symbol=obj.arr[0][9])
                        event_mkt_exec_inc_order_no.set()
                db.session.add(new_row)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()  # Rollback in case of error
            tranData = PriceRow.query.order_by(PriceRow.id).all()
            tranDataDict = [row.to_dict() for row in tranData] # Convert data to a list of dictionaries
            socketio.emit('floorsheet', {'database': tranDataDict})

        # remaining orders to get filled
        if placedOrders[i-1][5] == 'Buy':
            placedOrders[i-1][4] -= obj.sellOB[0][1]
        else:
            placedOrders[i-1][4] -= obj.buyOB[0][1]
        socketio.emit('placed_orders', {'placedOrders': placedOrders})

        if placedOrders[i-1][4] == 0: # when all qty is filled
            del MKT_Orders[0]

    # When the best bid/ask qty > mkt order's qty
    else:
        # update the top bid/ask
        topAskBid = obj.sellOB if placedOrders[i-1][5] == 'Buy' else obj.buyOB
        topAskBid[0][0] = int(topAskBid[0][0] * (1 - (placedOrders[i-1][4] / topAskBid[0][1]))) if topAskBid[0][0] > 1 else topAskBid[0][0]
        topAskBid[0][1] -= placedOrders[i-1][4]
        if placedOrders[i-1][5] == 'Buy':
            socketio.emit('order_book', {'sellOB': topAskBid, 'ltp': topAskBid[0][2], 'sym': placedOrders[i-1][1]})
            # deduct collateral
            socketio.emit('deduct_req', {'amt': obj.sellOB[0][2] * placedOrders[i-1][4], 'uname': placedOrders[i-1][7]})
        else:
            socketio.emit('order_book', {'buyOB': topAskBid, 'ltp': topAskBid[0][2], 'sym': placedOrders[i-1][1]})

        # Add data to database
        with app.app_context():
            try:
                rand = maker(obj.arr)
                if placedOrders[i-1][5] == 'Buy':
                    if placedOrders[i-1][2] == placedOrders[i-1][4]:
                        new_row = PriceRow(conID=genConID(False, i), buyerID=users[placedOrders[i-1][7]].uid, sellerID=rand[3], qty=placedOrders[i-1][4], rate=obj.sellOB[0][2], buyerName=users[placedOrders[i-1][7]].name, sellerName=rand[8], symbol=obj.arr[0][9])
                    else:
                        event_place_order_inc_order_no.wait()
                        event_mkt_exec_inc_order_no.clear()
                        Orders += 1
                        new_row = PriceRow(conID=genConID(True, Orders), buyerID=users[placedOrders[i-1][7]].uid, sellerID=rand[3], qty=placedOrders[i-1][4], rate=obj.sellOB[0][2], buyerName=users[placedOrders[i-1][7]].name, sellerName=rand[8], symbol=obj.arr[0][9])
                        event_mkt_exec_inc_order_no.set()
                else:
                    if placedOrders[i-1][2] == placedOrders[i-1][4]:
                        new_row = PriceRow(conID=genConID(False, i), buyerID=rand[2], sellerID=users[placedOrders[i-1][7]].uid, qty=placedOrders[i-1][4], rate=obj.buyOB[0][2], buyerName=rand[7], sellerName=users[placedOrders[i-1][7]].name, symbol=obj.arr[0][9])
                    else:
                        event_place_order_inc_order_no.wait()
                        event_mkt_exec_inc_order_no.clear()
                        Orders += 1
                        new_row = PriceRow(conID=genConID(True, Orders), buyerID=rand[2], sellerID=users[placedOrders[i-1][7]].uid, qty=placedOrders[i-1][4], rate=obj.buyOB[0][2], buyerName=rand[7], sellerName=users[placedOrders[i-1][7]].name, symbol=obj.arr[0][9])
                        event_mkt_exec_inc_order_no.set()
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


def orderMatch_sim(obj):

    def genOB(rate):
        # top bid & ask prices in order book
        bidPrices = []; askPrices = []
        bidPrices = genPrices(rate, 'bids', obj.prices)
        askPrices = genPrices(rate, 'asks', obj.prices)

        # generating asks order book
        for i in range(0, TOP_BIDSASKS_NO): # filling each row in order book
            obj.sellOB.append([0, 0, askPrices[i]]) # initializing row data: [orders, qty, price]
            brokers = [] # collects all the brokers in the list for that particular price
            if(i == 0):
                idx = 0
                while(idx < len(obj.arr) and obj.arr[idx][5] == obj.sellOB[i][2]):
                    idx += 1
                idx -= 1
                if(idx != -1):
                    for x in obj.queue:
                        count = -1
                        for y in x:
                            if(obj.sellOB[i][2] == y[5]):
                                obj.sellOB[i][1] += y[4]
                                brokers.append(y[3])
                                count += 1
                                if(count == idx):
                                    break
                        if(obj.sellOB[i][1] != 0):
                            break
            else:
                for x in obj.queue:
                    for y in x:
                        if(obj.sellOB[i][2] == y[5]): # to find orders data realted to current price in queue
                            obj.sellOB[i][1] += y[4] # fetching qty and adding
                            brokers.append(y[3]) # append all brokers
                        else:
                            break
                    if(obj.sellOB[i][1] != 0):
                        break
            if(len(brokers) == 0):
                obj.sellOB[i][1] = int(random.triangular(10, 1300, 200)) # random qty between 10-1300, mostly being of 100-300
                obj.sellOB[i][0] = int(random.triangular(1, 20, 7)) # random qty between 1-20, mostly being around 7
            else:
                obj.sellOB[i][0] = len(obj.remove_duplicates(brokers)) # total orders
        
        # generating bids order book
        for i in range(0, TOP_BIDSASKS_NO):
            obj.buyOB.append([0, 0, bidPrices[i]])
            brokers = []
            for x in obj.queue:
                for y in x:
                    if(obj.buyOB[i][2] == y[5]):
                        obj.buyOB[i][1] += y[4]
                        brokers.append(y[2])
                    else:
                        break
                if(obj.buyOB[i][1] != 0):
                    break
            if(len(brokers) == 0):
                obj.buyOB[i][1] = int(random.triangular(10, 1300, 200))
                obj.buyOB[i][0] = int(random.triangular(1, 20, 7))
            else:
                obj.buyOB[i][0] = len(obj.remove_duplicates(brokers))

        
        with lock_emit:
            if obj.mkt_ex_mode == False:
                socketio.emit('order_book', {'sellOB': obj.sellOB, 'buyOB': obj.buyOB, 'ltp': obj.arr[0][5], 'sym': obj.arr[0][9]})
            else:
                socketio.emit('order_book', {'sellOB': obj.sellOB, 'buyOB': obj.buyOB, 'sym': obj.arr[0][9]})

    def linear_price():
        if len(obj.arr) > 1:
            price_diff = round(obj.arr[1][5] - obj.arr[0][5], 1)
            if abs(price_diff) > 0.3:
                factor = abs(price_diff)*10 - 1
                i = 1 if price_diff>0 else -1

                time_diff = obj.arr[1][6] - obj.arr[0][6]
                time_diff = time_diff.total_seconds()

                def next_rate(i):
                    return round(obj.arr[0][5] + 0.1*i, 1)
                
                while True:
                    flag = 0
                    while next_rate(i) != obj.arr[1][5]:
                        for price in obj.prices:
                            if price == next_rate(i):
                                i = i+1 if i>0 else i-1
                                flag = 1
                                factor += 1
                                break
                        if(flag == 0):
                            break
                        flag = 0
                    if next_rate(i) == obj.arr[1][5]:
                        break
                    obj.sellOB.clear()
                    obj.buyOB.clear()
                    # print("--------------------------------")
                    genOB(next_rate(i))
                    i = i+1 if i>0 else i-1

                    # if there are open market orders of this symbol
                    if len(MKT_Orders) != 0 and placedOrders [MKT_Orders[0]-1] [1] == obj.arr[0][9]:
                        MKT_execute(obj)
                        obj.mkt_ex_mode = True

                    else:
                        if obj.subThreads > 0 or obj.mkt_ex_mode == True:
                            if time_diff/factor > 1:
                                time.sleep(1)
                            else:
                                time.sleep(time_diff/factor)
                        else:
                            if time_diff/factor > 2:
                                time.sleep(time_diff/factor)
                            else:
                                time.sleep(2)
                obj.mkt_ex_mode = False

    def matchOrder():
        if obj.buyOB[0][2] == obj.sellOB[0][2]: # when top bid & ask price match
            for idx, x in enumerate(obj.queue):
                for y in x:
                    if obj.buyOB[0][2] == y[5]:
                        # Add data to database
                        with lock_db:
                            with app.app_context():
                                try:
                                    new_row = PriceRow(conID=y[1], buyerID=y[2], sellerID=y[3], qty=y[4], rate=y[5], buyerName=y[7], sellerName=y[8], symbol=y[9])
                                    db.session.add(new_row)
                                    db.session.commit()
                                except IntegrityError:
                                    db.session.rollback()  # Rollback in case of error
                                    
                                if obj.arr[0][9] == symbol:
                                    tranData = PriceRow.query.order_by(PriceRow.id).all()
                                    tranDataDict = [row.to_dict() for row in tranData] # Convert data to a list of dictionaries
                                    socketio.emit('floorsheet', {'database': tranDataDict})
                            
                        # if a LMT order matches
                        if y[1][8:9] == '1':
                            for indx in range(9, 16):
                                if y[1][indx] != '0':
                                    global placedOrders
                                    placedOrders[int(y[1][indx:])-1][4] = 0
                                    socketio.emit('placed_orders', {'placedOrders': placedOrders})
                                    break
                        
                        linear_price()

                        del obj.queue[idx][0]  # delete first order of that price
                        # if orders in that price is empty
                        if len(obj.queue[idx]) == 0:
                            del obj.queue[idx]  # delete that element of queue
                            del obj.prices[idx]  # delete that particular price from prices list
                        del obj.arr[0]
                        return
                    else:
                        break

    
    with lock_start:
        event_firstEmit.wait()
        socketio.emit('stock_list', {'ltp': obj.arr[0][5], 'sym': obj.arr[0][9], 'scripName': obj.name, 'prevClose': obj.prevClose})

        if obj.arr[0][9] == symbol: # for default asset to display
            socketio.emit('display_asset', {'sym': symbol})

    sym = obj.arr[0][9]
    while len(obj.arr) != 0:
        genOB(obj.arr[0][5])
        matchOrder()
        obj.sellOB.clear()
        obj.buyOB.clear()

        if obj.subThreads > 0:
            obj.event_start_subThread.set()
            obj.event_place_LMT.wait()

            obj.event_start_subThread.clear()
            obj.event_place_LMT.clear()
        
        # when to wrap up order matching simulation
        if finish:
            # if there are any market orders, fill them first
            if not MKT_Orders:
                # after all the market orders have been filled
                barrier.wait()
                # select one thread to delete the user's limit order
                with lock_del:
                    global event_terminate
                    if not event_terminate:
                        event_terminate = True
                        del_orders()
                        socketio.emit('placed_orders', {'placedOrders': placedOrders})
                break
    
    if obj.arr:  # case where market is abruptly terminated by the admin, fill remaining orders to the db
        with lock_db:
            with app.app_context():
                try:
                    # Create a list of PriceRow objects
                    new_rows = [
                        PriceRow(conID=row[1], buyerID=row[2], sellerID=row[3], qty=row[4], rate=row[5], buyerName=row[7], sellerName=row[8], symbol=row[9])
                        for row in obj.arr
                    ]
                    # Add all rows in a single operation
                    db.session.add_all(new_rows)
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()  # Rollback in case of an error
        obj.arr.clear()  # empty the list of extracted data

    socketio.emit('finished_matching', {'sym': sym})
    print(sym, "Finished matching.")

    barrier.wait()
    if barrier.wait() == 0:
        socketio.emit('mkt_closed')
        global finished
        finished = True

        # add balance and collateral
        with app.app_context():
            rows = PriceRow.query.all()  # Fetch all rows
            for row in rows:
                if (row.conID[8:9] == '1'):
                    if int(row.buyerID) >= 100:
                        users[get_user(row.buyerID)].balance[row.symbol] += float(row.qty)
                    if int(row.sellerID) >= 100:
                        users[get_user(row.sellerID)].collateral += float(row.qty) * float(row.rate)


def LMT_place(Rate, Qty, OrderNo, type, key):
    OrderData = []
    
    def genTime(idx):
        if idx-1 < 0:
            return assets[key].arr[idx][6] + timedelta(microseconds=-1)
        if idx+1 == len(assets[key].arr):
            return assets[key].arr[idx][6] + timedelta(microseconds=1)
        else:
            return assets[key].arr[idx-1][6] + (assets[key].arr[idx][6] - assets[key].arr[idx-1][6]) / 2

    def write_orderData(idx):
        nonlocal OrderData
        rand = maker(assets[key].arr)
        if type == 'Buy':
            OrderData = ['', genConID(False, OrderNo), users[placedOrders[OrderNo-1][7]].uid, rand[3], Qty, Rate, genTime(idx), users[placedOrders[OrderNo-1][7]].name, rand[8], assets[key].arr[0][9]]
        else:
            OrderData = ['', genConID(False, OrderNo), rand[2], users[placedOrders[OrderNo-1][7]].uid, Qty, Rate, genTime(idx), rand[7], users[placedOrders[OrderNo-1][7]].name, assets[key].arr[0][9]]

    def in_the_end():
        global placedOrders
        placedOrders[OrderNo-1][6] = True
        socketio.emit('placed_orders', {'placedOrders': placedOrders})
        assets[key].subThreads -= 1
        if assets[key].subThreads == 0:
            assets[key].event_place_LMT.set()
            assets[key].skip = False
        else:
            assets[key].skip = True

    with lock_orderPlacing[key]:
        if assets[key].skip == False:
            assets[key].event_start_subThread.wait() # wait for main-thread to check if orders have matched before overwriting the new order to the data structure
        
        compare = (lambda x, y: x < y) if type == 'Buy' else (lambda x, y: x > y)
        for idx, next in enumerate(assets[key].arr):
            if compare(next[5], Rate):
                write_orderData(idx)
                assets[key].arr.insert(idx, OrderData)
                encounter = False
                for i, price in enumerate(assets[key].prices):
                    if price == Rate:
                        assets[key].queue[i].insert(0, OrderData)
                        encounter = True
                        break
                    elif price > Rate:
                        assets[key].prices.insert(i, Rate)
                        assets[key].queue.insert(i, [OrderData])
                        encounter = True
                        break
                if encounter == False:
                    assets[key].prices.append(Rate)
                    assets[key].queue.append([OrderData])
                in_the_end()
                return

            elif next[5] == Rate:
                count = 0
                while True:
                    if idx+1 != len(assets[key].arr) and assets[key].arr[idx+1][5] == Rate:
                        idx += 1
                        count += 1
                    else:
                        write_orderData(idx) if idx+1 == len(assets[key].arr) else write_orderData(idx+1)
                        assets[key].arr.insert(idx+1, OrderData)
                        for i, price in enumerate(assets[key].prices):
                            if price == Rate:
                                assets[key].queue[i].insert(count+1, OrderData)
                                break
                        break
                in_the_end()
                return

        if type == 'Buy':
            write_orderData(len(assets[key].arr)-1)
            assets[key].arr.append(OrderData)
            assets[key].prices.insert(0, Rate)
            assets[key].queue.insert(0, [OrderData])
        else:
            write_orderData(len(assets[key].arr)-1)
            assets[key].arr.append(OrderData)
            assets[key].prices.append(Rate)
            assets[key].queue.append([OrderData])
        in_the_end()


# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = users.get(username)

        if user and user.check_password(password):
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# Wrap up order matching simulation (admin's route)
@app.route('/close_market', methods=['POST'])
def close_market():
    print("Received Message:", request.json)  # Debugging: Print the received message
    global finish
    finish = True
    socketio.emit('wrap_up')
    return jsonify({"status": "success", "message": "Market closure received"})

# Net Settlement admin's route
@app.route('/settlement')
def manage_all_users():
    pass

# Home page
@app.route("/")
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("index.html")

# Handle the form submission (AJAX)
@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        global Orders
        
        Rate = request.form.get('rate')
        Rate = float(Rate) if Rate else None  # Set to None if empty
        Qty = int(request.form.get('qty'))
        action = request.form.get('action')  # Get whether it's a buy or sell order
        event_mkt_exec_inc_order_no.wait()
        event_place_order_inc_order_no.clear()
        Orders += 1
        event_place_order_inc_order_no.set()

        if not Rate: # market execution
            placedOrders.append([Orders, symbol, Qty, 'MKT', Qty, action, False, session['username']])
            MKT_Orders.append(Orders)
        else: # limit order
            placedOrders.append([Orders, symbol, Qty, Rate, Qty, action, False, session['username']])
            for idx, asset in enumerate(assets):
                if asset.arr and asset.arr[0][9] == placedOrders[Orders-1][1]:
                    asset.subThreads += 1
                    threading.Thread(target=LMT_place, args=(Rate, Qty, Orders, action, idx)).start()  # run process in background
                    break
        socketio.emit('placed_orders', {'placedOrders': placedOrders})

        return "Order successfully placed", 200
    except Exception as e:
        print(f"Error: {str(e)}")  # Debugging line for error
        return str(e), 400


# Deduct collateral on purchase
@socketio.on('deduct_buy')
def handle_deduction(data):
    user = users.get(session['username'])
    user.collateral -= data.get('amt')

    if 'username' in session: # only consider to emit updated collateral to client if user is logged in
        # if it was a market order, collateral is deducted as it gets filled
        if data.get('uname'):
            if session['username'] == data.get('uname'): # so check if that same user hasn't logged out before emiting the collateral
                socketio.emit('user_info', {'collateral': user.collateral}, room=request.sid)
        # in cases of limit order, collateral can be deducted all at once and emit
        else:
            socketio.emit('user_info', {'collateral': user.collateral}, room=request.sid)

# Deduct asset balance on sell
@socketio.on('deduct_sell')
def handle_deduction(data):
    user = users.get(session['username'])
    user.balance[symbol] -= data.get('qty')
    
    if 'username' in session:
        socketio.emit('user_info', {'balance': user.balance}, room=request.sid)


@socketio.on('connect')
def handle_conncet():
    if 'username' in session:
        if finished:
            socketio.emit('mkt_closed')

        socketio.emit('user_info', {
            'uname': users.get(session['username']).username,
            'name': users.get(session['username']).name,
            'balance': users.get(session['username']).balance,
            'collateral': users.get(session['username']).collateral
            }, room=request.sid)
        
        socketio.emit('placed_orders', {'placedOrders': placedOrders})

    event_firstEmit.set()

@socketio.on('scrip_selected')
def handle_scrip_selected(data):
    global symbol

    scrip = data.get('scrip')
    
    symbol = scrip


# Runner & debugger
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    print("Creating threads ...")
    for obj in assets:
        threading.Thread(target=orderMatch_sim, args=(obj,)).start()

    socketio.run(app, debug=True, use_reloader=False)