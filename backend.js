        async function fetchItems() {
            const response = await fetch('/items');
            const items = await response.json();
            const itemList = document.getElementById('itemList');
            itemList.innerHTML = '';  // Clear existing items

            items.forEach(item => {
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.value = item.item_id;
                checkbox.id = `item-${item.item_id}`;
                const label = document.createElement('label');
                label.htmlFor = `item-${item.item_id}`;
                label.appendChild(document.createTextNode(`${item.item_name} - ₹${item.price}`));
                itemList.appendChild(checkbox);
                itemList.appendChild(label);
                itemList.appendChild(document.createElement('br'));
            });
        }

        async function fetchTransactions() {
            const response = await fetch('/transactions');
            const transactions = await response.json();
            const transactionTable = document.getElementById('transactionTableBody');
            transactionTable.innerHTML = '';  // Clear existing rows

            transactions.forEach(transaction => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${transaction.transaction_id}</td>
                    <td>${transaction.student_id}</td>
                    <td>${transaction.item_id}</td>
                    <td>${transaction.amount}</td>
                    <td>${new Date(transaction.timestamp).toLocaleString()}</td>
                `;
                transactionTable.appendChild(row);
            });
        }

        async function addItem() {
            const itemName = prompt("Enter item name:");
            const itemPrice = parseFloat(prompt("Enter item price:"));
            if (itemName && !isNaN(itemPrice)) {
                const response = await fetch('/items', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ item_name: itemName, price: itemPrice })
                });
                const result = await response.json();
                alert(result.message);
                await fetchItems();  // Refresh items list
            } else {
                alert("Invalid input. Please try again.");
            }
        }

        async function editItem() {
            const itemId = parseInt(prompt("Enter item ID to edit:"));
            const itemName = prompt("Enter new item name:");
            const itemPrice = parseFloat(prompt("Enter new item price:"));
            if (!isNaN(itemId) && itemName && !isNaN(itemPrice)) {
                const response = await fetch(`/items/${itemId}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ item_name: itemName, price: itemPrice })
                });
                const result = await response.json();
                alert(result.message);
                await fetchItems();  // Refresh items list
            } else {
                alert("Invalid input. Please try again.");
            }
        }

        async function deleteItem() {
            const itemName = prompt("Enter item name to delete:");
            if (itemName) {
                const response = await fetch(`/items/delete`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ item_name: itemName })
                });
                const result = await response.json();
                alert(result.message);
                await fetchItems();  // Refresh items list
            } else {
                alert("Invalid input. Please try again.");
            }
        }




        async function checkout() {
            const selectedItems = Array.from(document.querySelectorAll('input[type=checkbox]:checked'))
                                       .map(cb => cb.value);
            const rfid = document.getElementById('rfidInput').value;

            const response = await fetch('/checkout', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ rfid, items: selectedItems })
            });
            const result = await response.json();

            if (response.ok) {
                alert(result.message);
                await fetchTransactions();  // Refresh transactions after checkout
                generateReceipt(rfid, selectedItems, result.new_balance);
            } else {
                alert(result.error || "An error occurred");
            }
        }

        function generateReceipt(rfid, itemIds, newBalance) {
            fetch(`/items`)
                .then(response => response.json())
                .then(items => {
                    const selectedItems = items.filter(item => itemIds.includes(item.item_id.toString()));
                    const timestamp = new Date().toISOString().replace(/[-:.]/g, "").slice(0, 15);
                    
                    // Create receipt HTML
                    const receiptHtml = `
                        <div id="receipt" style="padding: 10px; border: 1px solid #ccc;">
                            <h2>INDIAN LANGUAGE SCHOOL CANTEEN</h2>
                            <p>RFID: ${rfid}</p>
                            <h4>Items:</h4>
                            <ul>
                                ${selectedItems.map(item => `<li>${item.item_name} - ₹${item.price}</li>`).join('')}
                            </ul>
                            <p><strong>New Balance: ₹${newBalance}</strong></p>
                            <p>Timestamp: ${new Date().toLocaleString()}</p>
                        </div>
                    `;
                    document.getElementById('receiptPreview').innerHTML = receiptHtml;
                    document.getElementById('receiptPreview').style.display = 'block';
                    document.getElementById('downloadButton').style.display = 'block';
                });
        }

        function downloadReceipt() {
            html2canvas(document.querySelector("#receipt")).then(canvas => {
                const timestamp = new Date().toISOString().replace(/[-:.]/g, "").slice(0, 15);
                const filename = `receipt_${timestamp}.png`;
                const link = document.createElement('a');
                link.href = canvas.toDataURL();
                link.download = filename;
                link.click();
            });
        }

        window.onload = async () => {
            await fetchItems();
            await fetchTransactions();  // Fetch transactions on page load
        };