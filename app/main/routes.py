from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.financeiro.models import Transaction
from app.extensions import db
from sqlalchemy import func, extract
from datetime import datetime
from config import Config

main_bp = Blueprint('main', __name__, template_folder='templates')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}

@main_bp.route('/')
@login_required
def index():
    """Página inicial/Dashboard com resumo financeiro."""
    today = datetime.now()
    current_month = today.month
    current_year = today.year

    total_balance = sum(wallet.current_balance for wallet in current_user.wallets)

    monthly_filter = [
        Transaction.user_id == current_user.id,
        extract('month', Transaction.date) == current_month,
        extract('year', Transaction.date) == current_year]

    monthly_income_result = db.session.scalar(
        db.select(func.coalesce(func.sum(Transaction.amount), 0.00)).where(
            *monthly_filter,
            Transaction.type == 'R'))
    
    monthly_income = float(monthly_income_result)

    monthly_expenses_result = db.session.scalar(
        db.select(func.coalesce(func.sum(Transaction.amount), 0.00)).where(
            *monthly_filter,
            Transaction.type == 'D'))
    
    monthly_expenses = float(monthly_expenses_result)

    latest_transactions = Transaction.query.filter_by(user_id=current_user.id) \
                                           .filter_by(is_recurrent=False) \
                                           .order_by(Transaction.date.desc()) \
                                           .limit(5) \
                                           .all()

    context = {
        'total_balance': total_balance,
        'latest_transactions': latest_transactions,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'title': 'Dashboard'
    }

    return render_template('main/dashboard.html', **context, **footer)
