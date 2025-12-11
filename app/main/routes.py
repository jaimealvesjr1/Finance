from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.financeiro.models import Wallet, RevenueTransaction, Expense 
from app.extensions import db
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from config import Config

main_bp = Blueprint('main', __name__, template_folder='templates')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}

@main_bp.route('/')
@login_required
def index():
    today = datetime.now()
    current_month = today.month
    current_year = today.year

    total_balance = sum(wallet.current_balance for wallet in current_user.wallets)

    monthly_revenue_filter = [
        RevenueTransaction.user_id == current_user.id,
        extract('month', RevenueTransaction.date) == current_month,
        extract('year', RevenueTransaction.date) == current_year
    ]
    
    monthly_paid_expense_filter = [
        Expense.user_id == current_user.id,
        extract('month', Expense.payment_date) == current_month,
        extract('year', Expense.payment_date) == current_year,
        Expense.is_paid == True
    ]
    
    monthly_pending_expense_filter = [
        Expense.user_id == current_user.id,
        extract('month', Expense.due_date) == current_month,
        extract('year', Expense.due_date) == current_year,
        Expense.is_paid == False
    ]

    monthly_income_result = db.session.scalar(
        db.select(func.coalesce(func.sum(RevenueTransaction.amount), 0.00)).where( 
            *monthly_revenue_filter
        )
    )
    monthly_income = float(monthly_income_result)

    monthly_expenses_result = db.session.scalar(
        db.select(func.coalesce(func.sum(Expense.amount), 0.00)).where( 
            *monthly_paid_expense_filter
        )
    )
    monthly_expenses = float(monthly_expenses_result)

    monthly_pending_result = db.session.scalar(
        db.select(func.coalesce(func.sum(Expense.amount), 0.00)).where(
            *monthly_pending_expense_filter
        )
    )
    monthly_pending_expenses = float(monthly_pending_result)

    latest_paid_expenses = Expense.query.filter_by(user_id=current_user.id, is_paid=True) \
                                         .order_by(Expense.payment_date.desc()) \
                                         .limit(5) \
                                         .all()
    
    dates = [today - timedelta(days=x*30) for x in range(5, -1, -1)]
    chart_labels = [d.strftime('%b') for d in dates]
    
    chart_receitas = []
    chart_despesas = []

    for d in dates:
        rec = db.session.scalar(
            db.select(func.coalesce(func.sum(RevenueTransaction.amount), 0)).where(
                RevenueTransaction.user_id == current_user.id,
                extract('month', RevenueTransaction.date) == d.month,
                extract('year', RevenueTransaction.date) == d.year,
            )
        )
        desp = db.session.scalar(
            db.select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == current_user.id,
                extract('month', Expense.payment_date) == d.month,
                extract('year', Expense.payment_date) == d.year,
                Expense.is_paid == True
            )
        )
        chart_receitas.append(float(rec))
        chart_despesas.append(float(desp))

    context = {
        'total_balance': total_balance,
        'latest_transactions': latest_paid_expenses,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'monthly_pending_expenses': monthly_pending_expenses,
        'chart_labels': chart_labels,
        'chart_receitas': chart_receitas,
        'chart_despesas': chart_despesas,
        'title': 'Dashboard'
    }

    return render_template('main/dashboard.html', **context, **footer)
