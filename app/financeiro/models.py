from app.extensions import db
from datetime import datetime, date
from sqlalchemy import func 
from decimal import Decimal

class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    initial_balance = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    transactions = db.relationship('RevenueTransaction', backref='wallet', lazy='dynamic')
    expenses = db.relationship('Expense', backref='wallet', lazy='dynamic')
    
    def __repr__(self):
        return f'<Wallet {self.name}>'

    @property
    def current_balance(self):
        total_receipts = db.session.scalar(
            db.select(func.coalesce(func.sum(RevenueTransaction.amount), Decimal(0))).where(
                RevenueTransaction.wallet_id == self.id,
                RevenueTransaction.is_received == True
            ))
        
        total_paid_expenses = db.session.scalar(
            db.select(func.coalesce(func.sum(Expense.amount), Decimal(0))).where( 
                Expense.wallet_id == self.id,
                Expense.is_paid == True
            ))
        
        receipts = total_receipts if total_receipts is not None else Decimal(0)
        paid_expenses = total_paid_expenses if total_paid_expenses is not None else Decimal(0)

        return self.initial_balance + receipts - paid_expenses
    

class RevenueCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(1), default='R', nullable=False) 
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    transactions = db.relationship('RevenueTransaction', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<RevenueCategory {self.name}>'
    
# ExpenseGroup REMOVIDO

class ExpenseCategory(db.Model):
    # ExpenseItem adaptado para ExpenseCategory (Ponto 1)
    __tablename__ = 'expense_category' 
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    
    # group_id REMOVIDO
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    expenses = db.relationship('Expense', backref='category', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<ExpenseCategory {self.name}>'


class RevenueTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    due_date = db.Column(db.Date, nullable=False, index=True)
    receipt_date = db.Column(db.DateTime, nullable=True, index=True)
    is_received = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    is_recurrent = db.Column(db.Boolean, default=False, nullable=False)
    frequency = db.Column(db.String(50), nullable=True)
    last_launch_date = db.Column(db.DateTime, nullable=True)
    
    type = db.Column(db.String(1), default='R', nullable=False) 

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('revenue_category.id'), nullable=False)
    
    def __repr__(self):
        return f'<RevenueTransaction {self.description} | R${self.amount} | Recebido: {self.is_received}>'

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    date = db.Column(db.Date, default=date.today, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=True)
    is_paid = db.Column(db.Boolean, default=False, nullable=False)

    is_recurrent = db.Column(db.Boolean, default=False, nullable=False)
    frequency = db.Column(db.String(50), nullable=True)
    last_launch_date = db.Column(db.DateTime, nullable=True)
    
    category_id = db.Column(db.Integer, db.ForeignKey('expense_category.id'), nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False) 
    
    def __repr__(self):
        return f'<Expense {self.description} | R${self.amount} | Pago: {self.is_paid}>'

class Transfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    source_wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    target_wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    source_wallet = db.relationship('Wallet', foreign_keys=[source_wallet_id], backref='outgoing_transfers')
    target_wallet = db.relationship('Wallet', foreign_keys=[target_wallet_id], backref='incoming_transfers')

    def __repr__(self):
        return f'<Transfer R${self.amount} from {self.source_wallet.name} to {self.target_wallet.name}>'
