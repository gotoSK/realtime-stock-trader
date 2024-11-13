document.addEventListener('DOMContentLoaded', function() {
    var socket = io();
    var prevClose = parseFloat(document.getElementById("prevclose").textContent);
    
    // Store the last known values
    var lastSellOB = [];
    var lastBuyOB = [];
    var lastLTP = "N/A";
    var lastDatabase = [];

    // Initialize an empty array to store LTP values
    var ltpData = [];
    var labels = []; // For x-axis labels (e.g., timestamps or point numbers)

    // Function to update the order book
    function updateOrderBook(sellOB, buyOB, ltp) {
        var orderBookTableBody = document.getElementById('order-book-table-body');
        orderBookTableBody.innerHTML = '';  // Clear current table content

        // Use provided sellOB or fallback to last known sellOB
        var sellOrders = sellOB ? sellOB.slice().reverse() : lastSellOB.slice().reverse();

        // Insert rows for flipped 'sellOB'
        sellOrders.forEach(function(order) {
            var row = document.createElement('tr');
            order.forEach(function(value) {
                var cell = document.createElement('td');
                cell.textContent = value;
                row.appendChild(cell);
            });
            orderBookTableBody.appendChild(row);
        });

        // Use provided LTP or fallback to last known LTP
        var ltpValue = ltp ? ltp : lastLTP;
        
        // Insert a single row for 'LTP'
        var ltpRow = document.createElement('tr');
        var ltpCell = document.createElement('td');
        ltpCell.setAttribute('colspan', '3');  // Make it span 3 columns
        ltpCell.textContent = 'LTP: ' + ltpValue;
        ltpCell.style.textAlign = 'left';  // Align LTP to the left
        ltpRow.appendChild(ltpCell);
        orderBookTableBody.appendChild(ltpRow);

        // Use provided buyOB or fallback to last known buyOB
        var buyOrders = buyOB ? buyOB : lastBuyOB;

        // Insert rows for 'buyOB'
        buyOrders.forEach(function(order) {
            var row = document.createElement('tr');
            order.forEach(function(value) {
                var cell = document.createElement('td');
                cell.textContent = value;
                row.appendChild(cell);
            });
            orderBookTableBody.appendChild(row);
        });
    }

    // Function to update the floorsheet
    function updateFloorsheet(database) {
        var floorsheetTableBody = document.getElementById('floorsheet-table-body');
        floorsheetTableBody.innerHTML = '';  // Clear current floorsheet table content

        // Use provided database or fallback to last known database
        var floorsheetData = database ? database.slice().reverse() : lastDatabase.slice().reverse();

        // Insert rows for floorsheet with updated format
        floorsheetData.forEach(function(entry) {
            var row = document.createElement('tr');

            // Calculate amount = qty * rate
            var amount = entry.qty * entry.rate;

            // Add cells for each column
            var idCell = document.createElement('td');
            idCell.textContent = entry.id;
            row.appendChild(idCell);

            var conIDCell = document.createElement('td');
            conIDCell.textContent = entry.conID;
            row.appendChild(conIDCell);

            var qtyCell = document.createElement('td');
            qtyCell.textContent = entry.qty;
            row.appendChild(qtyCell);

            var rateCell = document.createElement('td');
            rateCell.textContent = entry.rate;
            row.appendChild(rateCell);

            var amountCell = document.createElement('td');
            amountCell.textContent = amount.toFixed(2);  // Keep 2 decimal places for amount
            row.appendChild(amountCell);

            var buyerNameCell = document.createElement('td');
            buyerNameCell.textContent = entry.buyerName;
            row.appendChild(buyerNameCell);

            var sellerNameCell = document.createElement('td');
            sellerNameCell.textContent = entry.sellerName;
            row.appendChild(sellerNameCell);

            floorsheetTableBody.appendChild(row);
        });
    }

    // Get the canvas context for drawing the chart
    var ctx = document.getElementById('ltpChart').getContext('2d');
    // Create a real-time line chart for LTP
    var ltpChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,  // X-axis labels
            datasets: [{
                label: 'Last Traded Price (LTP)',
                data: ltpData,  // Y-axis data for LTP
                borderColor: 'rgba(75, 192, 192, 1)',  // Line color
                backgroundColor: 'rgba(75, 192, 192, 0.2)',  // Background color
                borderWidth: 1,
                fill: false,  // Don't fill under the line
                pointRadius: 0,  // Remove the big dots from the line
                pointHoverRadius: 0  // Disable hover effect on the points
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: false  // Adjust this based on LTP values
                }
            }
        }
    });

    // Listen for 'order_book' event from the server
    socket.on('order_book', function(data) {
        // Update last known values if new data is provided
        if (data.sellOB) lastSellOB = data.sellOB;  // Update sellOB
        if (data.buyOB) lastBuyOB = data.buyOB;      // Update buyOB
        if (data.ltp) lastLTP = data.ltp;            // Update LTP
        // Update the order book with new or previous values
        updateOrderBook(data.sellOB, data.buyOB, data.ltp);

        // Add the new LTP value to the chart data
        ltpData.push(data.ltp);
        // Optionally, add labels (like time or index for the x-axis)
        labels.push(new Date().toLocaleTimeString());  // Use timestamp as label
        // Limit the number of data points to keep the chart manageable
        // if (ltpData.length > 50) {
        //     ltpData.shift();  // Remove the oldest data point
        //     labels.shift();  // Remove the oldest label
        // }
        // Update the chart to display the new LTP value
        ltpChart.update();
    });

    // Listen for 'floorsheet' event from the server
    socket.on('floorsheet', function(data) {
        // Update last known database if new data is provided
        if (data.database) lastDatabase = data.database;

        // Update the floorsheet with new or previous values
        updateFloorsheet(data.database);
    });

    // Toggle between Chart, Database and Stats
    $('#chart-container-btn').click(function() {
        $(this).addClass('active');
        $('#database-container-btn').removeClass('active');
        $('#stats-container-btn').removeClass('active');
        $('#chart-container').show();
        $('#database-container').hide();
        $('#stats-container').hide();
    });
    $('#database-container-btn').click(function() {
        $(this).addClass('active');
        $('#chart-container-btn').removeClass('active');
        $('#stats-container-btn').removeClass('active');
        $('#chart-container').hide();
        $('#database-container').show();
        $('#stats-container').hide();
    });
    $('#stats-container-btn').click(function() {
        $(this).addClass('active');
        $('#chart-container-btn').removeClass('active');
        $('#database-container-btn').removeClass('active');
        $('#chart-container').hide();
        $('#database-container').hide();
        $('#stats-container').show();
    });

    // Handle form submission via AJAX to avoid page reload
    $('.order-form').on('submit', function(event) {
        event.preventDefault();  // Prevent default form submission
        var formData = $(this).serialize();  // Serialize the form data
        var form = $(this); // Save reference to the current form

        // Validate before sending AJAX request
        var rate = parseFloat(form.find('#rate').val());
        var qty = parseInt(form.find('#qty').val());
        var action = form.find('input[name="action"]').val();

        if (action == 'Buy' && rate > lastSellOB[0][2]) {
            alert('Buy Limit exceeds top bid price');
            return;
        }
        else if (action == 'Sell' && rate < lastBuyOB[0][2]) {
            alert('Sell Limit falls short to top ask price');
            return;
        }

        // Validation
        if (rate != 0) {
            let p1 = (prevClose*0.9).toString();
            let decimalIndex = p1.indexOf('.');
            if (decimalIndex !== -1 && p1.length - decimalIndex - 1 === 2) {
                p1 = parseFloat(p1.slice(0, -1)) + 0.1;
            } else {
                p1 = parseFloat(p1.slice(0, -1));
            }
            let p2 = (prevClose*1.1).toString();
            decimalIndex = p2.indexOf('.');
            if (decimalIndex !== -1 && p2.length - decimalIndex - 1 === 2) {
                p2 = parseFloat(p2.slice(0, -1));
            }
            if (rate < p1 || rate > p2) {
                alert(`You're breaking circuit. Rate must be within (${p1}(${prevClose*0.9}) - ${p2}(${prevClose*1.1})).`);
                return;
            }
            if (!/^\d+(\.\d{1})?$/.test(rate)) {
                alert(`Rate must be multiple of 0.1. ${rate}`);
                return;
            }
        }
        if (qty < 10) {
            alert('Quantity must be of at least 10 units.');
            return;
        }

        // Submit form data via AJAX
        $.ajax({
            url: '/place_order',
            method: 'POST',
            data: formData,
            success: function(response) {
                alert(action + ' order placed successfully!');
                form.find('input[type="number"]').val('');  // Clear the rate and quantity inputs
            },
            error: function(error) {
                alert('Error placing ' + action + ' order.');
            }
        });
    });

    // Toggle between Limit Order and Market Execution forms
    $('#limit-order-btn').click(function() {
        $(this).addClass('active');
        $('#market-execution-btn').removeClass('active');
        $('#limit-order-form').show();
        $('#market-execution-form').hide();
    });
    $('#market-execution-btn').click(function() {
        $(this).addClass('active');
        $('#limit-order-btn').removeClass('active');
        $('#market-execution-form').show();
        $('#limit-order-form').hide();
    });

    // Listen for 'placed_orders' event from the server
    socket.on('placed_orders', function(data) {
        var placedOrders = data.placedOrders;

        // Clear the current table content
        $('#open-orders-table-body').empty();
        $('#filled-orders-table-body').empty();

        placedOrders.forEach(function(order) {
            if (order[0] != null) {
                var row = '<tr>' +
                    '<td>' + order[1] + '</td>' + // Symbol
                    '<td>' + order[2] + '</td>' + // Qty
                    '<td>' + order[3] + '</td>' + // Rate
                    '<td>' + order[4] + '</td>' + // Rem.
                    '<td>' + order[5] + '</td>';  // Type (Buy/Sell)

                // If Success is False, show loading circle
                if (!order[6]) {
                    row += '<td><div class="loading-circle"></div></td>';
                } else {
                    row += '<td>Yes</td>';
                }

                row += '</tr>';

                // If Rem. is greater than 0, it's an open order
                if (order[4] > 0) {
                    $('#open-orders-table-body').append(row);
                } else {
                    $('#filled-orders-table-body').append(row);
                }
            }
        });
    });

    // Toggle between "Open Orders" and "Filled Orders"
    $('#open-orders-btn').click(function() {
        $(this).addClass('active');
        $('#filled-orders-btn').removeClass('active');
        $('#open-orders').show();
        $('#filled-orders').hide();
    });
    $('#filled-orders-btn').click(function() {
        $(this).addClass('active');
        $('#open-orders-btn').removeClass('active');
        $('#filled-orders').show();
        $('#open-orders').hide();
    });
});