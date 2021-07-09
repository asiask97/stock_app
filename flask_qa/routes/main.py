from flask import Blueprint, Flask, session, redirect, url_for, render_template, request, flash
from werkzeug.security import check_password_hash, generate_password_hash
import os
from flask_sqlalchemy import SQLAlchemy
import datetime
from flask_qa.extensions import db
from flask_qa.models import users, portfolio, transactions
import requests

main = Blueprint('main', __name__)

# helper functions 
def api_request(symbol):
    
    try:
        api_key = os.environ.get("API_KEY") 
        response = requests.get(f"https://cloud.iexapis.com/stable/stock/{symbol}/quote?token={api_key}")
        #response.raise_for_status()
    except requests.RequestException:
        return None
    
    result = response.json()
    return{
        'name': result["companyName"],
        "symbol": result["symbol"],
        "price": float(result["latestPrice"]),
    }


def string_to_number_converter(s):
    try:
        return int(s)
    except ValueError:
        return "error"



@main.route("/")
def home():
    if request.method == "GET":
        
        # Make sure user loged in 
        if session.get("user_id") is None:
            return redirect("/login")

        # Getting user portfoilio
        user_portfolio = portfolio.query.filter_by(user = session["user_id"]).first()
        all_stocks_cash = 0

        # Getting the symbols
        for stock in user_portfolio:

            live_data = api_request(stock.stock_symbol)
            amount_bought = stock.stock_amount
            stock.live_price = live_data['price']
            all_stocks_cash += amount_bought * live_data['price']

        # Displaying users cash status
        user_cash = users.query.filter_by(_id = session["user_id"]).first()
        with_stocks = round(all_stocks_cash + user_cash.cash, 2)

        # Loading portfoilio on to webside
        return render_template("index.html", user_portfolio=user_portfolio, with_out=round(user_cash.cash, 2), with_stocks=with_stocks)

    else:
        flash("something went wrong")
        return redirect("/login")


@main.route("/login", methods=["GET", "POST"])
def login():
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("must provide username")
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return redirect("/login")

        # Query database for username and password
        user_check = users.query.filter_by(username = request.form.get("username")).first()   
        
        # Ensure username exists and password is correct
        if user_check == None or not check_password_hash(user_check._hash, request.form.get("password")):
            flash("invalid username and/or password")
            return redirect("/login")

        # Remember which user has logged in
        session["user_id"] = id_check

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")



@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'POST':

        # Query for username
        username_check = users.query.filter_by(username = request.form.get("username")).first()

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must provide username")
            return redirect("/register")

        # Ensure password was submitted
        elif not request.form.get("password"):
           flash("Must provide password")
           return redirect("/register")
        
        # Ensure confirmation password was submitted
        elif not request.form.get("confirmation"):
            flash("Must repeat password")
            return redirect("/register")

        # Ensure if both passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords must match")
            return redirect("/register")

        # Ensure username is not taken        
        elif username_check:
            flash("Username already taken")
            return redirect("/register")

        else:
            
            # Insert user into database
            username = request.form.get("username")
            password = generate_password_hash(request.form.get("password"))
            new_user =  users(username = username, _hash = password)
            db.session.add(new_user)
            db.session.commit()
            
            # Redirect user to login page so user can login
            flash('User Registered')
            return redirect("/login")

    else:
        return render_template("register.html")    

@main.route("/quote", methods=["GET", "POST"])
def quote():
    if request.method == 'POST':
        
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            flash("Must provide a symbol")
            return redirect("/quote")

        # Serch for qoute in API
        result = api_request(request.form.get("symbol"))

        # Error check the result (in case its empty)
        if result == None:
            flash("Could not find a quote")
            return redirect("/quote")

        # Display the serch results
        else:
            name = result['name']
            symbol = result['symbol']
            price = result['price']
            
            return render_template("quoted.html", name=name, symbol=symbol, price=price)

    else:
        # Make sure user loged in 
        if session.get("user_id") is None:
            return redirect("/login")
        else:
            return render_template("quote.html")

@main.route("/buy", methods=["GET", "POST"])
def buy():
    if request.method == "POST":
    
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            flash("Must provide symbol")
            return redirect("/buy")

        # Ensure amount was submitted
        check = string_to_number_converter(request.form.get("shares"))
        if check == "error":
            flash("Must provide an int")
            return redirect("/buy")
        elif not request.form.get("shares") or int(request.form.get("shares")) <= 0:
            flash("Must provide an amount")
            return redirect("/buy")

        # Serch for qoute in API
        symbol_data = api_request(request.form.get("symbol"))
        
        # Error check the result (in case its empty)
        if symbol_data == None:
            flash("Could not find symbol")
            return redirect("/buy")
        
        # Ensure if user can afford to buy this stock IF they can get new account balance
        amount_requested = float(request.form.get("shares")) * float(symbol_data['price'])
        account_balance = users.query.filter_by(_id = session["user_id"]).first()
        new_balance = float(account_balance.cash) - amount_requested 

        if amount_requested > float(account_balance.cash):
            flash("Not enough funds in the account")
            return redirect("/buy")

        else:
            # Update data in TRANSACTIONS log
            transaction_type = "buy"
            symbol = request.form.get("symbol")
            new_transaction =  transactions(user = session["user_id"], _type = transaction_type, stock_symbol= symbol.upper(), price = symbol_data['price'], stock_amount = request.form.get("shares"))
            db.session.add(new_transaction)
            db.session.commit()

            # Update data in PORTFOLIO
            # if this stock is not in portfoilio then insert it, if it is then update its amount
            stock_check = portfolio.query.filter_by(stock_symbol = symbol.upper(), user = session["user_id"]).first()

            if stock_check == None:
                
                # Update portfolio
                new_stock =  portfolio(user = session["user_id"], stock_name = symbol_data["name"], stock_symbol= symbol.upper(), stock_amount = request.form.get("shares"), live_price = symbol_data['price'])
                db.session.add(new_stock)
                db.session.commit()

                # Update users
                find_user = users.query.filter_by(_id = session["user_id"]).first()
                find_user.cash = new_balance
                db.session.commit()
                flash("Bought")
                return redirect("/")
            
            else:
                
                # Update portfolio
                find_symbol = portfolio.query.filter_by(stock_symbol = symbol.upper(), user = session["user_id"]).first()
                find_symbol.stock_amount = find_symbol.stock_amount + int(request.form.get("shares"))
                db.session.commit()

                # Update users
                find_user = users.query.filter_by(_id = session["user_id"]).first()
                find_user.cash = new_balance
                db.session.commit()
                flash("Bought")
                return redirect("/")

    else:
        if session.get("user_id") is None:
            return redirect("/login")
        else:
            return render_template("buy.html")

@main.route("/sell", methods=["GET", "POST"])
def sell():
    if request.method == "POST":
        # Make sure user loged in 
        if session.get("user_id") is None:
            return redirect("/login")

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            flash("Must provide symbol")
            return redirect("/sell")
        
        # Ensure amount was submitted
        if not request.form.get("shares") or int(request.form.get("shares")) <= 0:
            flash("Must provide an amount")
            return redirect("/sell")

        # Check current value of stock
        stock_data = api_request(request.form.get("symbol"))
        selling_val = stock_data["price"]*int(request.form.get("shares"))
        symbol = request.form.get("symbol")
        
        # Update portfolio and drop if the amount of shares is = 0
        current_shares = portfolio.query.filter_by(stock_symbol = symbol.upper(), user = session["user_id"]).first()
        
        if current_shares.stock_amount - int(request.form.get("shares")) == 0:
            portfolio.query.filter_by(stock_symbol = symbol.upper(), user = session["user_id"]).delete()
        elif current_shares.stock_amount - int(request.form.get("shares")) < 0:
            flash("Cannot sell more shares than you own")
            return redirect("/sell")
        else:
            # Update portfolio
            find_symbol = portfolio.query.filter_by(stock_symbol = symbol.upper(), user = session["user_id"]).first()
            find_symbol.stock_amount = find_symbol.stock_amount - int(request.form.get("shares"))
            db.session.commit()

        # Update TRANSACTIONS table
        transaction_type = "sell"
        amount = "-" + request.form.get("shares")
        new_transaction = transactions(user = session["user_id"], _type = transaction_type, stock_symbol= symbol.upper(), price = stock_data['price'], stock_amount = amount)
        db.session.add(new_transaction)
        db.session.commit()
        
        # Update amount of cash ib user table

        find_user = users.query.filter_by(_id = session["user_id"]).first()
        find_user.cash = find_user.cash + selling_val
        db.session.commit()
        flash("Sold")

        return redirect("/")
    else:
        
        stock_data = portfolio.query.filter_by( user = session["user_id"]).all()
        print(stock_data)
        
        return render_template("sell.html", stock_data=stock_data)

@main.route("/history")
def history():
    if request.method == "GET":
        
        # Make sure user loged in 
        if session.get("user_id") is None:
            return redirect("/login")

        trans = transactions.query.filter_by(user = session["user_id"]).all()
        return render_template("history.html", trans=trans)
        
    else:
        return render_template("history.html")

@main.route("/logout")
def logout():

    # Forget any user_id
    session.clear()
    return redirect("/")
