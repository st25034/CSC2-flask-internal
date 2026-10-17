import datetime
import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Calculate total cost based on cart contents and selected addons
def calculate_total(cart, selected_addons):
    donut_subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
    addon_subtotal = sum(selected_addons.values())

    total = donut_subtotal + addon_subtotal

    discount_applied = False

    if total > 70:
        total = total * 0.90
        discount_applied = True

    return total, donut_subtotal, addon_subtotal, discount_applied

def initialise_database():
    with sqlite3.connect('donut_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT,
                customer_name TEXT,
                items TEXT,
                addons TEXT,
                total REAL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
@app.route('/') 
def index():
    donuts, addons = load_data()
    cart = session.get('cart', {})
    selected_addons = session.get('selected_addons', {})
    total, donut_subtotal, addon_subtotal, discount_applied = calculate_total(cart, selected_addons)

    if total > 50:
        flash("You are ordering a lot! Consider calling us for a special deal.")

    return render_template('index.html', donuts=donuts, addons=addons, cart=cart, selected_addons=selected_addons, donut_subtotal=donut_subtotal, addon_subtotal=addon_subtotal, total=total, discount_applied=discount_applied)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/invoices')
def invoices():
    return render_template('invoices.html')

# Order history page show past orders from the database
@app.route('/orders')
def order_history():
    with sqlite3.connect('donut_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders ORDER BY date DESC")
        rows = cursor.fetchall()

    orders = []

    for row in rows:
        orders.append({
            'order_id': row[0],
            'invoice_number': row[1],
            'customer_name': row[2],
            'items': json.loads(row[3]),
            'addons': json.loads(row[4]),
            'total': row[5],
            'date': row[6]
        })

    return render_template('order_history.html', orders=orders)

# Delete an order from the database by ID
@app.route('/cancel_saved_order/<int:order_id>', methods=['POST'])
def cancel_saved_order(order_id):
    with sqlite3.connect('donut_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
        conn.commit()

    flash("Order cancelled")
    return redirect(url_for('order_history'))

def load_data():
    try:
        with open('data/donuts.json') as file:
            donuts = json.load(file)

        with open('data/addons.json') as file:
            addons = json.load(file)

        return donuts, addons 
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading data: {e}")
        return {}, {}

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    donut = request.form['donut']
    quantity = int(request.form['quantity'])
    donuts, addons = load_data()
    cart = session.get('cart', {})

    if donut not in donuts:
        flash("Invalid donut selected.")
        return redirect(url_for('index'))

    if donut in cart:
        new_quantity = cart[donut]['quantity'] + quantity
    else:
        new_quantity = quantity

    if new_quantity > donuts[donut]['stock']:
        flash(f"Not enough {donut} in stock. Only {donuts[donut]['stock']} available.")
        return redirect(url_for('index'))

    if donut in cart:
        cart[donut]['quantity'] = new_quantity
    else:
        cart[donut] = {
            'price': donuts[donut]['price'],
            'quantity': quantity
        }

    session['cart'] = cart
    session.modified = True
    flash(f"{quantity} {donut}(s) added to cart.")
    return redirect(url_for('index'))

# Remove an item from the shopping cart
@app.route('/remove_from_cart/<item>')
def remove_from_cart(item):
    cart = session.get('cart', {})

    if item in cart:
        del cart [item]
        session ['cart'] = cart
        session.modified = True
        flash(f"Removed all {item} from the cart.")
    else:
        flash("Item not found in cart")
        
    return redirect(url_for('cart'))

# Add selected addons to the session
@app.route('/select_addon', methods=['POST'])
def select_addon():
    selected_addons = session.get('selected_addons', {})
    _, addons = load_data() # we only need addons

    selected_keys = request.form.getlist('addons')

    if not selected_keys:
        flash("No add-ons selected.")
        return redirect(url_for('index'))

    for addon in selected_keys:
        if addon in addons:
            selected_addons[addon] = float(addons[addon]['price'])

    session['selected_addons'] = selected_addons
    session.modified = True

    flash(f"{len(selected_addons)} add-on(s) added to cart.")

    return redirect(url_for('index'))

# Remove an add-on from the shopping cart
@app.route('/remove_addon/<addon>')
def remove_addon(addon):
    selected_addons = session.get('selected_addons', {})

    if addon in selected_addons:
        del selected_addons[addon]
        session['selected_addons'] = selected_addons
        session.modified = True
        flash(f"Removed {addon} from the cart.")
    else:
        flash("Add-on not found in cart")

    return redirect(url_for('cart'))

# Clear cart and addons from the session (cancel current order)
@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    session.pop('cart', None)
    session.pop('selected_addons', None)
    session.modified = True

    flash("Order Cancelled. Your cart has been emptied.")

    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    selected_addons = session.get('selected_addons', {})

    total, donut_subtotal, addon_subtotal, discount_applied = calculate_total(
        cart, selected_addons
    )

    return render_template(
        'cart.html',
        cart=cart,
        selected_addons=selected_addons,
        total=total,
        donut_subtotal=donut_subtotal,
        addon_subtotal=addon_subtotal,
        discount_applied=discount_applied
    )

#Check out current order
@app.route('/checkout', methods=['POST'])
def checkout():

    #Validate customer name
    customer_name = request.form['customer_name'].strip().title()
    # Check if the customer name has been entered, if not, display message
    # and return to home page (index.html)
    if not customer_name:
        flash("Customer name is required.")
        return redirect(url_for('index'))

    # Get selected donuts (cart) and selected addons from the session
    cart = session.get('cart', {})
    selected_addons = session.get('selected_addons', {})
    
    # Prevent checkout with an empty cart
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for('index'))

    # Calculate total
    total, donut_subtotal, addon_subtotal, discount_applied = calculate_total(cart, selected_addons)

    subtotal = donut_subtotal + addon_subtotal
    discount = subtotal - total

    # Create invoice number and date
    invoice_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    invoice_number = f"INV_{customer_name.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    
    #Save order to SQLite database
    try:
        with sqlite3.connect('donut_shop.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (invoice_number, customer_name, items, addons, total)
                VALUES (?, ?, ?, ?, ?)
            ''', (invoice_number, customer_name, json.dumps(cart), json.dumps(selected_addons), total))
            conn.commit()

    except sqlite3.Error as e:
        flash("Database error occurred.")
        print(f"SQLite error: {e}")

    # Update the stock in donuts.json
    try: 
        with open('data/donuts.json', 'r') as file:
            donut_data = json.load(file)

        for donut_name, details in cart.items():
            if donut_name in donut_data:
                donut_data[donut_name]['stock'] -= details['quantity']

                if donut_data[donut_name]['stock'] < 0:
                    donut_data[donut_name]['stock'] = 0

        with open('data/donuts.json', 'w') as file:
            json.dump(donut_data, file, indent=4)
    
    except OSError as e:
        flash("Could not update stock file.")
        print(f"Error updating stock: {e}")

    # Generate invoice file
    invoice_filename = f"{invoice_number}.txt"
    try:
        with open(invoice_filename, 'w') as f:
            f.write("DONUT SHOP INVOICE\n")
            f.write(f"Invoice Number: {invoice_number}\n")
            f.write(f"Customer Name: {customer_name}\n")
            f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("Items:\n")
            for item, details in cart.items():
                f.write(f"- {item}: {details['quantity']} x ${details['price']} = ${details['quantity'] * details['price']:.2f}\n")

            f.write("\nAdd-Ons:\n")
            for addon, price in selected_addons.items():
                f.write(f"- {addon}: ${price:.2f}\n")

            f.write("\nSummary\n")
            f.write(f"Subtotal: ${subtotal:.2f}\n")

            if discount_applied:
                f.write(f"Discount (10%): -${discount:.2f}\n")

            f.write(f"Total: ${total:.2f}\n")

    except OSError as e:
        flash("Could not generate invoice file.")
        print(f"Error writing invoice: {e}")

    # Clear cart and add-ons after checkout
    session.pop('cart', None)
    session.pop('selected_addons', None)
    session.modified = True

    # Display invoice information on confirmation page
    return render_template(
        'invoices.html',
        customer_name=customer_name,
        cart=cart,
        selected_addons=selected_addons,
        total=total,
        donut_subtotal=donut_subtotal,
        addon_subtotal=addon_subtotal,
        invoice_date=invoice_date,
        invoice_number=invoice_number,
        discount_applied=discount_applied,
        subtotal=subtotal,
        discount=discount
    )

if __name__ == '__main__':
    initialise_database()
    app.run(debug=True)