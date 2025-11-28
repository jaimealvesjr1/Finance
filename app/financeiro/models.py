from app.extensions import db
from datetime import datetime

class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    initial_balance = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    transactions = db.relationship('Transaction', backref='wallet', lazy='dynamic')

    def __repr__(self):
        return f'<Wallet {self.name}>'

    @property
    def current_balance(self):
        """Calcula o saldo atual da carteira baseado nas transações."""
        total_receipts = db.session.scalar(
            db.select(db.func.sum(Transaction.amount)).where(
                Transaction.wallet_id == self.id,
                Transaction.type == 'R'
            ))
        
        total_expenses = db.session.scalar(
            db.select(db.func.sum(Transaction.amount)).where(
                Transaction.wallet_id == self.id,
                Transaction.type == 'D'
            ))
        
        receipts = total_receipts if total_receipts is not None else 0
        expenses = total_expenses if total_expenses is not None else 0

        return self.initial_balance + receipts - expenses
    
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(1), nullable=False) 
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name} ({self.type})>'
    
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    type = db.Column(db.String(1), nullable=False) 

    is_recurrent = db.Column(db.Boolean, default=False)
    frequency = db.Column(db.String(50), nullable=True)

    last_launch_date = db.Column(db.DateTime, nullable=True) 

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    
    def __repr__(self):
        return f'<Transaction {self.description} | R${self.amount} ({self.type})>'
