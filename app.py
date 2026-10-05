import json
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Calculate total cost based on cart contents and selected addons
def calculate_total(cart, selected_addons):
    donut_subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
    addon_subtotal = sum(selected_addons.values())

    total = donut_subtotal + addon_subtotal

    return total, donut_subtotal, addon_subtotal

@app.route('/') 
def index():
    donuts, addons = load_data()
    cart = session.get('cart', {})
    selected_addons = session.get('selected_addons', {})
    total, donut_subtotal, addon_subtotal = calculate_total(cart, selected_addons)

    if total > 50:
        flash("You are ordering a lot! Consider calling us for a special deal.")

    return render_template('index.html', donuts=donuts, addons=addons, cart=cart, selected_addons=selected_addons, donut_subtotal=donut_subtotal, addon_subtotal=addon_subtotal, total=total)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/invoices')
def invoices():
    return render_template('invoices.html')

@app.route('/orders')
def order_history():
    return render_template('order_history.html')

def load_data():
    with open('data/donuts.json') as file:
        donuts = json.load(file)

    with open('data/addons.json') as file:
        addons = json.load(file)

    return donuts, addons 

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
        cart[donut]['quantity'] += quantity
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
        
    return redirect(url_for('index'))

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


if __name__ == '__main__':
    app.run(debug=True)