from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.financeiro.models import Wallet, RevenueTransaction, Expense, RevenueCategory, ExpenseCategory
from app.extensions import db
from sqlalchemy import func, desc, asc, extract
from datetime import datetime, timedelta, date
from calendar import monthrange
from config import Config
from decimal import Decimal

main_bp = Blueprint('main', __name__, template_folder='templates')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}
TRANSFER_CATEGORY_NAME = 'Transferência'

def get_monthly_data(user_id, months_back=5, months_forward=6):
    today = date.today()
    labels = []
    revenues = []
    expenses = []
    balances = []
    
    start_range = -months_back
    end_range = months_forward + 1
    
    current_balance_accumulated = 0

    for i in range(start_range, end_range):
        target_month = today.month + i
        target_year = today.year
        
        while target_month > 12:
            target_month -= 12
            target_year += 1
        while target_month < 1:
            target_month += 12
            target_year -= 1
            
        month_name = date(target_year, target_month, 1).strftime('%b/%y')
        labels.append(month_name)
        
        _, last_day = monthrange(target_year, target_month)
        m_start = date(target_year, target_month, 1)
        m_end = date(target_year, target_month, last_day)
        
        if i <= 0:
            rev_sum = db.session.query(func.sum(RevenueTransaction.amount)).filter(
                RevenueTransaction.user_id == user_id,
                RevenueTransaction.is_received == True,
                RevenueTransaction.receipt_date >= m_start,
                RevenueTransaction.receipt_date <= m_end
            ).scalar() or 0
            
            exp_sum = db.session.query(func.sum(Expense.amount)).filter(
                Expense.user_id == user_id,
                Expense.is_paid == True,
                Expense.payment_date >= m_start,
                Expense.payment_date <= m_end
            ).scalar() or 0
        else:
            rev_sum = db.session.query(func.sum(RevenueTransaction.amount)).filter(
                RevenueTransaction.user_id == user_id,
                RevenueTransaction.due_date >= m_start,
                RevenueTransaction.due_date <= m_end
            ).scalar() or 0
            
            exp_sum = db.session.query(func.sum(Expense.amount)).filter(
                Expense.user_id == user_id,
                Expense.due_date >= m_start,
                Expense.due_date <= m_end
            ).scalar() or 0

        revenues.append(float(rev_sum))
        expenses.append(float(exp_sum))
        
        net_result = float(rev_sum) - float(exp_sum)
        balances.append(net_result)

    return {
        'labels': labels,
        'revenues': revenues,
        'expenses': expenses,
        'balances': balances
    }

def get_category_data(user_id):
    """Agrupa despesas e receitas por categoria (Referente ao ano atual para ter relevância)"""
    current_year = date.today().year
    
    # 1. Agrupar Despesas por Categoria
    expenses_query = db.session.query(
        ExpenseCategory.name,
        func.sum(Expense.amount)
    ).join(Expense).filter(
        Expense.user_id == user_id,
        extract('year', Expense.due_date) == current_year
    ).group_by(ExpenseCategory.name).all()
    
    # 2. Agrupar Receitas por Categoria
    revenues_query = db.session.query(
        RevenueCategory.name,
        func.sum(RevenueTransaction.amount)
    ).join(RevenueTransaction).filter(
        RevenueTransaction.user_id == user_id,
        extract('year', RevenueTransaction.due_date) == current_year
    ).group_by(RevenueCategory.name).all()
    
    return {
        'expense_labels': [e[0] for e in expenses_query],
        'expense_values': [float(e[1]) for e in expenses_query],
        'revenue_labels': [r[0] for r in revenues_query],
        'revenue_values': [float(r[1]) for r in revenues_query]
    }

@main_bp.route('/')
@login_required
def index():
    # 1. Totais Gerais (Mantido)
    total_revenues = db.session.query(func.sum(RevenueTransaction.amount)).filter_by(user_id=current_user.id, is_received=True).scalar() or 0
    total_expenses = db.session.query(func.sum(Expense.amount)).filter_by(user_id=current_user.id, is_paid=True).scalar() or 0
    balance = total_revenues - total_expenses
    
    # 2. Gráfico de Fluxo (Mantido)
    chart_data = get_monthly_data(current_user.id)
    
    # 3. NOVOS DADOS: Gráficos de Categoria (Ano Atual)
    category_data = get_category_data(current_user.id)
    
    # 4. NOVOS DADOS: Listas "Próximos 5"
    next_expenses = Expense.query.filter_by(
        user_id=current_user.id, 
        is_paid=False
    ).order_by(asc(Expense.due_date)).limit(5).all()
    
    next_revenues = RevenueTransaction.query.filter_by(
        user_id=current_user.id, 
        is_received=False
    ).order_by(asc(RevenueTransaction.due_date)).limit(5).all()
    
    return render_template('main/dashboard.html', 
                           title='Dashboard',
                           total_revenues=total_revenues,
                           total_expenses=total_expenses,
                           balance=balance,
                           chart_data=chart_data,
                           category_data=category_data,
                           next_expenses=next_expenses,
                           next_revenues=next_revenues,
                           now_date=date.today()) # <--- ADICIONADO AQUI: Passando a data de hoje

@main_bp.app_context_processor
def inject_notifications():
    if not current_user.is_authenticated:
        return dict()
        
    today = date.today()
    
    rev_count = RevenueTransaction.query.filter_by(
        user_id=current_user.id, is_received=False, due_date=today
    ).count()
    
    exp_count = Expense.query.filter_by(
        user_id=current_user.id, is_paid=False, due_date=today
    ).count()
    
    return dict(notif_revenue_today=rev_count, notif_expense_today=exp_count)

@main_bp.route('/clear_broadcast', methods=['POST'])
@login_required
def clear_broadcast():
    current_user.pending_message = None
    db.session.commit()
    return jsonify({'status': 'ok'})
