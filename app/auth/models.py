from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from sqlalchemy.ext.hybrid import hybrid_property
from app.financeiro.models import Wallet, RevenueCategory, RevenueTransaction, ExpenseGroup, ExpenseItem, Expense

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    access_due_date = db.Column(db.Date, nullable=True) 
    pending_message = db.Column(db.String(500), nullable=True)

    wallets = db.relationship('Wallet', backref='user', lazy='dynamic')
    categories = db.relationship('RevenueCategory', backref='user', lazy='dynamic')
    transactions = db.relationship('RevenueTransaction', backref='user', lazy='dynamic')
    
    expense_groups = db.relationship('ExpenseGroup', backref='user', lazy='dynamic')
    expense_items = db.relationship('ExpenseItem', backref='user', lazy='dynamic')
    expenses = db.relationship('Expense', backref='user', lazy='dynamic')

    def set_password(self, password):
        """Cria o hash da senha e armazena em password_hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """"Verifica se a senha fornecida corresponde ao hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_active(self):
        return True

    @property
    def is_functional_active(self): 
        today = date.today()
        return self.is_admin or (self.access_due_date and self.access_due_date >= today)
    
    @hybrid_property
    def is_active(self):
        today = date.today()
        return self.is_admin or (self.access_due_date and self.access_due_date >= today)
    
    def __repr__(self):
        return f'<User {self.username}>'
