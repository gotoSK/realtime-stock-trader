import csv
from datetime import datetime
import sys


allSymbols = [] # stores data of all symbols (for later use to extract data symbol-by-symbol)
prevDay = [] # previous day data of all securities


with open('./data/2024-08-01', 'r') as csv_file:
    csv_reader = csv.reader(csv_file)
    next(csv_reader)

    # attributes:                      id, contractID, Buyer, Seller, Qty, Rate, Time, Buyer Name, Seller Name, Symbol
    # attribute col-index (csv_reader): 0,          1,     4,      5,   6,    7,   14,         12,          13,      3

    currSym = None
    current = []

    for idx, line in enumerate(csv_reader):
        if currSym == None: # 1st itteration: initialize currSym
            currSym = line[3]
        
        if line[3] != currSym: # if next symbol is different append all previous data
            allSymbols.append(current)
            current = []
            currSym = line[3]
        
        try:
            dateTime = datetime.strptime(line[14], "%Y-%m-%dT%H:%M:%S.%f") # Convert time string to datetime object
        except ValueError as e:
            dateTime = datetime.strptime(line[14], "%Y-%m-%dT%H:%M:%S") # When time attribute dosen't contain value less than seconds

        # make a stack of all transaction data (of common symbol)
        current.append([line[0], line[1], line[4], line[5], int(line[6]), float(line[7]), dateTime, line[12], line[13], line[3]])

    # end of last itteration: append all the data of last symbol
    allSymbols.append(current)

# remove all securities of low volume
def refine():
    global allSymbols
    temp = []
    for sec in allSymbols:
        if len(sec) >= 100:
            temp.append(sec)
    allSymbols = temp
refine()

# Write data as a CSV file
with open('./data/all-securities.csv', 'w', newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["S.N.", "Symbol", "TotalTransactions"])
    for i, sec in enumerate(allSymbols):
        writer.writerow([i+1, sec[0][9], len(sec)])


# extracting previous day data
with open('./data/2024-07-31', 'r') as csv_file:
    csv_reader = csv.reader(csv_file)
    next(csv_reader)
    # attributes:                      stockId, Symbol, securityName, Rate
    # attribute col-index (csv_reader):     11,      3,           15,    7
    currSym = None
    for line in csv_reader:
        if currSym == None: # 1st itteration: initialize currSym
            currSym = line[3]
            prevDay.append([line[11], line[3], line[15], float(line[7])])
        
        if line[3] != currSym: # if next symbol is different append new data
            prevDay.append([line[11], line[3], line[15], float(line[7])])
            currSym = line[3]

# check if all symbols' data are available in previous day
def check():
    match_found = False
    miss = 0
    for i in allSymbols:
        for j in prevDay:
            if i[0][9] == j[1]:
                match_found = True
                break
        if match_found == False:
            print(i[0][9], "not found.")
            miss += 1
        else:
                match_found = False
    if miss > 0:
        print(miss, "symbols missing!")
        return False
    else:
        return True
if not check(): sys.exit()