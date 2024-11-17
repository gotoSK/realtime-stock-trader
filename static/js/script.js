document.addEventListener('DOMContentLoaded', function() {
    
    var socket = io();
    
    var prevClose = parseFloat(document.getElementById("prevclose").textContent);
    
    // Store the last known values
    var lastSellOB = sessionStorage.getItem('lastSellOB') ? JSON.parse(sessionStorage.getItem('lastSellOB')) || [] : []; 
    var lastBuyOB = sessionStorage.getItem('lastBuyOB') ? JSON.parse(sessionStorage.getItem('lastBuyOB')) || [] : [];
    
    var lastLTP = sessionStorage.getItem('lastLTP') ? parseFloat(sessionStorage.getItem('lastLTP')) : null;
    
    var lastDatabase = sessionStorage.getItem('lastDatabase') ? JSON.parse(sessionStorage.getItem('lastDatabase')) || [] : [];
    
    var placedOrders = sessionStorage.getItem('placedOrders') ? JSON.parse(sessionStorage.getItem('placedOrders')) || [] : [];
    
    let lastCheckTime = sessionStorage.getItem('lastCheckTime') ? sessionStorage.getItem('lastCheckTime') : Date.now();
    var ltpData = sessionStorage.getItem('ltpData') ? JSON.parse(sessionStorage.getItem('ltpData')) || [] : []; // For y-axis labels (price)
    var labels = sessionStorage.getItem('labels') ? JSON.parse(sessionStorage.getItem('labels')) || [] : []; // For x-axis labels (timestamps)
    
    var ctx = document.getElementById('priceChart').getContext('2d'); // Get the canvas context for drawing the chart

    var change = lastLTP != null ? (lastLTP - prevClose) / prevClose : 0.0;


    function load_OrderBook() {
        var orderBookTableBody = document.getElementById('order-book-table-body');
        orderBookTableBody.innerHTML = '';  // Clear current table content

        var sellOrders = lastSellOB.slice().reverse();

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
        
        // Insert a single row for 'LTP'
        if (lastLTP) {
            var ltpRow = document.createElement('tr');
            var ltpCell = document.createElement('td');
            ltpCell.setAttribute('colspan', '3');  // Make it span 3 columns
            ltpCell.textContent = 'LTP: ' + lastLTP;
            ltpCell.style.textAlign = 'left';  // Align LTP to the left
            ltpRow.appendChild(ltpCell);
            orderBookTableBody.appendChild(ltpRow);
        }

        // Insert rows for 'buyOB'
        lastBuyOB.forEach(function(order) {
            var row = document.createElement('tr');
            order.forEach(function(value) {
                var cell = document.createElement('td');
                cell.textContent = value;
                row.appendChild(cell);
            });
            orderBookTableBody.appendChild(row);
        });
    } load_OrderBook();

    // Create a real-time line chart for LTP
    var priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,  // X-axis labels
            datasets: [{
                label: 'Stock Price',  // Name of the dataset
                data: ltpData,  // Y-axis data for LTP arr
                borderColor: function() {
                    return ltpData[ltpData.length - 1] >= ltpData[1] ? 'rgba(0, 200, 0, 1)' : 'rgba(200, 0, 0, 1)';
                },  // Line color
                backgroundColor: function() {
                    // Create a gradient background for the line
                    var gradient = ctx.createLinearGradient(0, 0, 0, 400);
                    if (ltpData[ltpData.length - 1] >= ltpData[1]) {
                        // Green gradient for upward trend
                        gradient.addColorStop(0, 'rgba(0, 200, 0, 0.3)');
                        gradient.addColorStop(1, 'rgba(0, 200, 0, 0)');
                    } else {
                        // Red gradient for downward trend
                        gradient.addColorStop(0, 'rgba(200, 0, 0, 0.3)');
                        gradient.addColorStop(1, 'rgba(200, 0, 0, 0)');
                    }
                    return gradient;
                },
                borderWidth: 2,  // Line width
                fill: true,  // Don't fill the area under the line
                pointRadius: function(context) {
                    // Show a point only on the last data point
                    return context.dataIndex === ltpData.length - 1 ? 5 : 0;
                },
                pointHoverRadius: 3,  // Hover effect on the last point
                pointBackgroundColor: function() {
                    return ltpData[ltpData.length - 1] >= ltpData[1] ? 'rgba(0, 200, 0, 1)' : 'rgba(200, 0, 0, 1)';
                },  // Color for the last point
                pointBorderWidth: function(context) {
                    // Make the last point thicker
                    return context.dataIndex === ltpData.length - 1 ? 1 : 0;
                }
            }]
        },
        options: {
            scales: {
                x: {
                    grid: {
                        display: false,  // Hide gridlines for X-axis
                    },
                    ticks: {
                        color: '#ccc'  // X-axis label color
                    }
                },
                y: {
                    position: 'right', // Position price scale on the right side
                    grid: {
                        display: false,  // Hide gridlines for Y-axis
                    },
                    ticks: {
                        color: '#ccc'  // Y-axis label color
                    },
                    beginAtZero: false  // Stock prices don't start from zero
                }
            },
            plugins: {
                legend: {
                    display: false  // Disable legend to simplify the chart
                },
                tooltip: {
                    mode: 'index',  // Show all points at the same index
                    intersect: false,  // Show the tooltip on hover regardless of exact point
                    usePointStyle: true,  // Use point style in tooltip
                    callbacks: {
                        label: function(tooltipItem) {
                            return ' NPR ' + tooltipItem.raw;  // Custom label in tooltip
                        }
                    }
                }
            },
            elements: {
                line: {
                    tension: 0.4  // Smooth out the line
                }
            },
            hover: {
                mode: 'index',  // Show tooltip and hover effect on closest point along x-axis
                intersect: false  // Activate hover effect even when not intersecting with the line
            }
        }
    });

    function load_Floorsheet() {
        var floorsheetTableBody = document.getElementById('floorsheet-table-body');
        floorsheetTableBody.innerHTML = '';  // Clear current floorsheet table content

        // Use provided database or fallback to last known database
        var floorsheetData = lastDatabase.slice().reverse();

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
    } load_Floorsheet();

    function updateChart() {
        const currentTime = Date.now();
        if (currentTime-lastCheckTime < 60000) {
            // Add the new LTP value to the chart data
            if (ltpData.length == 0) {
                ltpData.push(prevClose);
                ltpData.push(lastLTP);
            }
            else ltpData[ltpData.length-1] = lastLTP;
            sessionStorage.setItem('ltpData', JSON.stringify(ltpData));
            
            // Add label (time for the x-axis)
            if (labels.length == 0) {
                labels.push('');
                labels.push(new Date().toLocaleTimeString());
                labels.push('');
                sessionStorage.setItem('labels', JSON.stringify(labels));
            }
        }
        else {
            lastCheckTime = currentTime;
            sessionStorage.setItem('lastCheckTime', lastCheckTime);
            labels[labels.length-1] = new Date().toLocaleTimeString();
            labels.push('');
            ltpData.push(lastLTP);
            sessionStorage.setItem('ltpData', JSON.stringify(ltpData));
            sessionStorage.setItem('labels', JSON.stringify(labels));
        }
        
        priceChart.update();
    }

    function load_placedOrders() {
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
                }
                
                // If Rem. is greater than 0, it's an open order
                if (order[4] > 0) {
                    row += '<td><a href="#">Edit</a> <a href="#">Del</a></td>';
                    row += '</tr>';
                    $('#open-orders-table-body').append(row);
                } else {
                    row += '</tr>';
                    $('#filled-orders-table-body').append(row);
                }
            }
        });
    } load_placedOrders();


    // Listen for 'order_book' event from the server
    socket.on('order_book', function(data) {
        // Update last known values if new data is provided
        if (data.sellOB) lastSellOB = data.sellOB;
        if (data.buyOB) lastBuyOB = data.buyOB;
        if (data.ltp) lastLTP = data.ltp;

        sessionStorage.setItem('lastSellOB', JSON.stringify(lastSellOB));
        sessionStorage.setItem('lastBuyOB', JSON.stringify(lastBuyOB));
        sessionStorage.setItem('lastLTP', lastLTP.toString());

        load_OrderBook();
        updateChart();
    });

    // Listen for 'floorsheet' event from the server
    socket.on('floorsheet', function(data) {
        // Update last known database if new data is provided
        if (data.database) lastDatabase = data.database;
        
        sessionStorage.setItem('lastDatabase', JSON.stringify(lastDatabase));

        load_Floorsheet();
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

        
        // Validation
        if (rate != 0) {
            if (action == 'Buy' && rate > lastSellOB[0][2]) {
                alert('Buy Limit exceeds top bid price');
                return;
            }
            else if (action == 'Sell' && rate < lastBuyOB[0][2]) {
                alert('Sell Limit falls short to top ask price');
                return;
            }

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
        if (data.placedOrders) placedOrders = data.placedOrders;
        sessionStorage.setItem('placedOrders', JSON.stringify(placedOrders));
        load_placedOrders();
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

    // ensure the chart values are saved before the page is unloaded (for data integrity &/or backup for unexpected interruptions)
    window.addEventListener("beforeunload", function () {
        sessionStorage.setItem('lastSellOB', JSON.stringify(lastSellOB));
        sessionStorage.setItem('lastBuyOB', JSON.stringify(lastBuyOB));
        sessionStorage.setItem('lastLTP', lastLTP.toString());
        sessionStorage.setItem('lastDatabase', JSON.stringify(lastDatabase));
        sessionStorage.setItem('lastCheckTime', lastCheckTime);
        sessionStorage.setItem('ltpData', JSON.stringify(ltpData));
        sessionStorage.setItem('labels', JSON.stringify(labels));
        sessionStorage.setItem('placedOrders', JSON.stringify(placedOrders));
    });
});