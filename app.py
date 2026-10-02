import json
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/') 
def index():
    donuts = load_data()
    return render_template('index.html', donuts=donuts)

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
    return donuts

if __name__ == '__main__':
    app.run(debug=True)