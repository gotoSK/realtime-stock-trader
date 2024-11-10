from datetime import datetime
import csv

# custom floorsheet
arr = []
# list to store unique prices in sorted manner
prices = []
# list of buy/sell orders lists sorted on basis of price-time
queue = []
# prev. day closing price
prevClose = None
# total no. of top buy/sell orders to display in order book
TOP_BIDSASKS_NO = 9
# order book for top bid & ask prices
buyOB = []; sellOB = []
# total no. of sub-threads in existance
subThreads = 0 
# OrderID of placed orders by user
Orders = 0
# all existing MKT orders' OrderID
MKT_Orders = []
# market execution mode
mkt_ex_mode = False
# all types of orders placed by user
placedOrders = []


def radixSort(arr):
    # Convert floats to integers by scaling
    scale_factor = 10 ** max(len(str(price).split('.')[1]) if '.' in str(price) else 0 for price in arr)
    int_arr = [int(price * scale_factor) for price in arr]

    # Perform radix sort on the integer array
    max_val = max(int_arr)
    exp = 1
    while max_val // exp > 0:
        counting_sort(int_arr, exp)
        exp *= 10

    # Convert back to floats
    sorted_arr = [price / scale_factor for price in int_arr]
    return sorted_arr

def counting_sort(arr, exp):
    n = len(arr)
    output = [0] * n
    count = [0] * 10

    # Count occurrences of each digit
    for i in range(n):
        index = (arr[i] // exp) % 10
        count[index] += 1

    # Update count[i] to be the actual position in output
    for i in range(1, 10):
        count[i] += count[i - 1]

    # Build the output array
    for i in range(n - 1, -1, -1):
        index = (arr[i] // exp) % 10
        output[count[index] - 1] = arr[i]
        count[index] -= 1

    # Copy output array to arr
    for i in range(n):
        arr[i] = output[i]

def remove_duplicates(lst):
    unique_list = []
    prev_item = None
    for item in lst:
        if item != prev_item:
            unique_list.append(item)
            prev_item = item
    return unique_list


def createQueue():
    # create queue containing list of order information as element
    for price in prices:
        temp = []
        for x in arr:
            if(price == x[5]):
                temp.append([x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9]])
        queue.append(temp)


# extracting all necessary info from the data set
with open('./data/2024-08-01', 'r') as csv_file:
    csv_reader = csv.reader(csv_file)
    next(csv_reader)
    # attributes:                  id, contractID, Buyer, Seller, Qty, Rate, Time, Buyer Name, Seller Name, Symbol
    # attribute index (csv_reader): 0,          1,     4,      5,   6,    7,   14,         12,          13,      3
    # attribute index (arr):        0,          1,     2,      3,   4,    5,    6,          7,           8,      9

    for line in csv_reader:
        if(line[3] == "GFCL"):
            dateTime = datetime.strptime(line[14], "%Y-%m-%dT%H:%M:%S.%f") # Convert time string to datetime object
            arr.append([line[0], line[1], line[4], line[5], int(line[6]), float(line[7]), dateTime, line[12], line[13], line[3]])
            prices.append(float(line[7]))
        else:
            break

# extracting prev. closing price of the security
with open('./data/security-last-trade-info.csv', 'r') as csv_file:
    csv_reader = csv.reader(csv_file)
    next(csv_reader)
    for line in csv_reader:
        if(line[1] == "GFCL"):
            prevClose = float(line[3])


arr = arr[::-1] # reverse imported floorsheet data
prices = remove_duplicates(radixSort(prices)) # sort the prices and remove duplicates
createQueue()