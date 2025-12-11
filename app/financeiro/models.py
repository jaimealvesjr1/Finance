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
            db.select(func.coalesce(func.sum(RevenueTransaction.amount), Decimal(0))).where( # Uso de Decimal(0)
                RevenueTransaction.wallet_id == self.id,
            ))
        
        # 2. Soma Despesas Pagas (Expense onde is_paid=True)
        total_paid_expenses = db.session.scalar(
            db.select(func.coalesce(func.sum(Expense.amount), Decimal(0))).where( # Uso de Decimal(0)
                Expense.wallet_id == self.id,
                Expense.is_paid == True
            ))
        
        # Remove conversão para float. O resultado é Decimal ou None.
        receipts = total_receipts if total_receipts is not None else Decimal(0)
        paid_expenses = total_paid_expenses if total_paid_expenses is not None else Decimal(0)

        # A operação agora é entre Decimais (self.initial_balance é Decimal)
        return self.initial_balance + receipts - paid_expenses
    

# --- MODELO RENOMEADO: Category -> RevenueCategory (SÓ PARA RECEITAS) ---
class RevenueCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    # Campo type mantido como 'R' para retrocompatibilidade no banco
    type = db.Column(db.String(1), default='R', nullable=False) 
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    transactions = db.relationship('RevenueTransaction', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<RevenueCategory {self.name}>'
    
# --- NOVOS MODELOS: HIERARQUIA DE DESPESA (ExpenseGroup / ExpenseItem) ---
class ExpenseGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    items = db.relationship('ExpenseItem', backref='group', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<ExpenseGroup {self.name}>'

class ExpenseItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    
    group_id = db.Column(db.Integer, db.ForeignKey('expense_group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    expenses = db.relationship('Expense', backref='item', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<ExpenseItem {self.name} ({self.group.name})>'

# --- MODELO RENOMEADO: Transaction -> RevenueTransaction (SÓ PARA RECEITAS) ---
class RevenueTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    type = db.Column(db.String(1), default='R', nullable=False) # Forçado para 'R'

    # Campos de recorrência do modelo original (agora ignorados no form de Receita)
    is_recurrent = db.Column(db.Boolean, default=False)
    frequency = db.Column(db.String(50), nullable=True)
    last_launch_date = db.Column(db.DateTime, nullable=True) 

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('revenue_category.id'), nullable=False)
    
    def __repr__(self):
        return f'<RevenueTransaction {self.description} | R${self.amount} (R)>'

# --- NOVO MODELO: Expense (Despesa Paga ou Pendente) ---
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Datas de Fluxo de Caixa
    date = db.Column(db.Date, default=date.today, nullable=False) # Data de competência/registro
    due_date = db.Column(db.Date, nullable=False) # Data de Vencimento
    payment_date = db.Column(db.DateTime, nullable=True) # Data de Pagamento
    is_paid = db.Column(db.Boolean, default=False, nullable=False) # Status de pagamento (CRÍTICO)

    # Recorrência
    is_recurrent = db.Column(db.Boolean, default=False, nullable=False)
    frequency = db.Column(db.String(50), nullable=True)
    last_launch_date = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos com a nova hierarquia
    item_id = db.Column(db.Integer, db.ForeignKey('expense_item.id'), nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id'), nullable=False) 
    
    def __repr__(self):
        return f'<Expense {self.description} | R${self.amount} | Pago: {self.is_paid}>'
