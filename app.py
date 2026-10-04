import json
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/') 
def index():
    donuts, addons = load_data()
    return render_template('index.html', donuts=donuts, addons=addons)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/checkout')
def checkout():
    return render_template('invoice.html')

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


if __name__ == '__main__':
    app.run(debug=True)