from flask import Flask, jsonify, request, send_from_directory, send_file
import mysql.connector
import os
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

app = Flask(__name__)

# Database connection setup (same database, different tables)
db = mysql.connector.connect(
    host="localhost",
    user="Ashwin",  # Your MySQL username
    password="Ash passwd123",  # Your MySQL password
    database="CANTEEN"  # Change to appropriate database name when needed
)

# Ensure the data directory exists
DATA_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)

# ------------------- Navigation Routes -------------------

@app.route('/')
def login():
    return send_from_directory(os.getcwd(), 'login.html')

@app.route('/index.html')
def cashier_interface():
    return send_from_directory(os.getcwd(), 'index.html')

@app.route('/admin-panel.html')
def admin_panel():
    return send_from_directory(os.getcwd(), 'admin_panel.html')

# ------------------- RFID Payment System -------------------

@app.route('/test', methods=['GET'])
def home():
    return "RFID Payment System Server is Running!"

@app.route('/items', methods=['GET'])
def get_items():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM items WHERE is_active = TRUE")
    items = cursor.fetchall()
    cursor.close()
    return jsonify(items)

@app.route('/items', methods=['POST'])
def add_item():
    data = request.get_json()
    item_name = data['item_name']
    price = data['price']
    cursor = db.cursor()
    cursor.execute("INSERT INTO items (item_name, price) VALUES (%s, %s)", (item_name, price))
    db.commit()
    cursor.close()
    return jsonify({"message": "Item added successfully"}), 201

@app.route('/items/<int:item_id>', methods=['PUT'])
def edit_item(item_id):
    data = request.get_json()
    item_name = data['item_name']
    price = data['price']
    cursor = db.cursor()
    cursor.execute("UPDATE items SET item_name = %s, price = %s WHERE item_id = %s", (item_name, price, item_id))
    db.commit()
    cursor.close()
    return jsonify({"message": "Item updated successfully"}), 200

@app.route('/items/delete', methods=['DELETE'])
def delete_item_by_name():
    data = request.get_json()
    item_name = data['item_name']

    cursor = db.cursor()
    cursor.execute("SELECT * FROM items WHERE item_name = %s AND is_active = TRUE", (item_name,))
    item = cursor.fetchone()

    if item:
        cursor.execute("UPDATE items SET is_active = FALSE WHERE item_name = %s", (item_name,))
        db.commit()
        cursor.close()
        return jsonify({"message": f"Item '{item_name}' marked as inactive"}), 200
    else:
        cursor.close()
        return jsonify({"message": f"Item '{item_name}' not found or already inactive"}), 404

@app.route('/student/<rfid>', methods=['GET'])
def get_student_balance(rfid):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, credits FROM students WHERE rfid_number = %s", (rfid,))
    student = cursor.fetchone()
    cursor.close()
    if student:
        return jsonify(student)
    else:
        return jsonify({"error": "Student not found"}), 404

@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    rfid = data['rfid']
    item_ids = data['items']

    cursor = db.cursor()
    cursor.execute("SELECT price FROM items WHERE item_id IN (%s)" % ','.join(['%s'] * len(item_ids)), item_ids)
    prices = cursor.fetchall()
    total_cost = sum(price[0] for price in prices)

    cursor.execute("SELECT id, credits, name FROM students WHERE rfid_number = %s", (rfid,))
    student = cursor.fetchone()
    if student:
        student_id = student[0]
        current_balance = student[1]
        student_name = student[2]
        if current_balance >= total_cost:
            new_balance = current_balance - total_cost
            cursor.execute("UPDATE students SET credits = %s WHERE rfid_number = %s", (new_balance, rfid))

            item_ids_str = ",".join(map(str, item_ids))
            cursor.execute("INSERT INTO transactions (student_id, item_ids, amount, timestamp) VALUES (%s, %s, %s, %s)",
                           (student_id, item_ids_str, total_cost, datetime.now()))

            db.commit()
            cursor.close()

            return jsonify({
                "message": "Payment successful!",
                "new_balance": new_balance,
                "student_name": student_name,
                "items": item_ids,
                "total_cost": total_cost
            }), 200
        else:
            cursor.close()
            return jsonify({"error": "Insufficient balance"}), 400
    else:
        cursor.close()
        return jsonify({"error": "Student not found"}), 404

@app.route('/generate-receipt', methods=['POST'])
def generate_receipt():
    data = request.get_json()
    student_name = data['student_name']
    item_ids = data['items']
    total_cost = data['total_cost']

    img = Image.new('RGB', (400, 300), color='white')
    d = ImageDraw.Draw(img)
    title_font = ImageFont.load_default()
    d.text((10, 10), "INDIAN LANGUAGE SCHOOL CANTEEN", fill=(0, 0, 0), font=title_font)
    d.text((10, 50), f"Student Name: {student_name}", fill=(0, 0, 0), font=title_font)
    d.text((10, 80), "Items Purchased:", fill=(0, 0, 0), font=title_font)

    y_position = 100
    for item_id in item_ids:
        d.text((10, y_position), f"Item ID: {item_id}", fill=(0, 0, 0), font=title_font)
        y_position += 20

    d.text((10, y_position), f"Total Cost: ₹{total_cost:.2f}", fill=(0, 0, 0), font=title_font)
    image_path = f'receipt_{int(datetime.now().timestamp())}.png'
    img.save(image_path)
    return send_file(image_path, as_attachment=True)

@app.route('/transactions/today', methods=['GET'])
def get_today_transactions():
    cursor = db.cursor(dictionary=True)
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT t.transaction_id, s.name, i.item_name, t.amount, t.timestamp
        FROM transactions t
        JOIN students s ON t.student_id = s.id
        JOIN items i ON FIND_IN_SET(i.item_id, t.item_ids) > 0
        WHERE DATE(t.timestamp) = %s
        ORDER BY t.timestamp DESC
    """, (today,))
    transactions = cursor.fetchall()
    cursor.close()
    return jsonify(transactions)

@app.route('/transactions', methods=['GET'])
def get_all_transactions():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transactions")
    transactions = cursor.fetchall()
    cursor.close()
    return jsonify(transactions)

# ------------------- Canteen Admin Panel -------------------

@app.route('/students', methods=['GET'])
def get_students():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    cursor.close()
    return jsonify(students)

@app.route('/update-credits', methods=['POST'])
def update_credits():
    data = request.get_json()
    student_id = data['id']
    amount = data['amount']
    increase = data['increase']

    cursor = db.cursor()
    cursor.execute("SELECT credits FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    if student:
        new_credits = student[0] + amount if increase else student[0] - amount
        cursor.execute("UPDATE students SET credits = %s WHERE id = %s", (new_credits, student_id))
        db.commit()
        cursor.close()
        return jsonify({"message": "Credits updated successfully."})
    else:
        cursor.close()
        return jsonify({"message": "Student not found."}), 404

if __name__ == "__main__":
    app.run(debug=True, host='192.168.100.6', port=5000)
