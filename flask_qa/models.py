from .extensions import db 
import datetime

# models
class users(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    username = db.Column( db.Text)
    _hash = db.Column("hash", db.Text)
    cash = db.Column(db.Float, default=1000.00)

class portfolio(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False,)
    stock_name = db.Column(db.Text)
    stock_symbol = db.Column(db.Text)
    stock_amount = db.Column(db.Integer) 
    live_price = db.Column(db.Float)

class transactions(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    _type = db.Column("type", db.String(10))
    stock_symbol = db.Column(db.Text)
    price = db.Column(db.Float)
    stock_amount = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable = False, default=datetime.datetime.utcnow)
