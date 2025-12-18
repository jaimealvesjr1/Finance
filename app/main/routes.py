from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.financeiro.models import Wallet, RevenueTransaction, Expense, RevenueCategory, ExpenseCategory
from app.extensions import db
from sqlalchemy import func, extract
from datetime import datetime, timedelta, date
from config import Config
from decimal import Decimal

main_bp = Blueprint('main', __name__, template_folder='templates')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}
TRANSFER_CATEGORY_NAME = 'Transferência'

@main_bp.route('/')
@login_required
def index():
    today = datetime.now()
    current_month = today.month
    current_year = today.year

    if not current_user.is_active:
        return render_template('main/dashboard.html', 
                               is_active=False,
                               title='Acesso Bloqueado', 
                               **footer)

    total_balance = sum(wallet.current_balance for wallet in current_user.wallets)

    monthly_received_revenue_result = db.session.scalar(
        db.select(func.coalesce(func.sum(RevenueTransaction.amount), Decimal(0.00)))
        .join(RevenueTransaction.category)
        .where(
            RevenueTransaction.user_id == current_user.id,
            extract('month', RevenueTransaction.receipt_date) == current_month,
            extract('year', RevenueTransaction.receipt_date) == current_year,
            RevenueTransaction.is_received == True,
            RevenueCategory.name != TRANSFER_CATEGORY_NAME
        )
    )
    monthly_received_revenue = float(monthly_received_revenue_result)

    monthly_receivable_revenue_result = db.session.scalar(
        db.select(func.coalesce(func.sum(RevenueTransaction.amount), Decimal(0.00)))
        .join(RevenueTransaction.category)
        .where(
            RevenueTransaction.user_id == current_user.id,
            extract('month', RevenueTransaction.due_date) == current_month,
            extract('year', RevenueTransaction.due_date) == current_year,
            RevenueTransaction.is_received == False,
            RevenueCategory.name != TRANSFER_CATEGORY_NAME
        )
    )
    monthly_receivable_revenue = float(monthly_receivable_revenue_result)

    monthly_paid_expenses_result = db.session.scalar(
        db.select(func.coalesce(func.sum(Expense.amount), Decimal(0.00)))
        .join(Expense.category)
        .where(
            Expense.user_id == current_user.id,
            extract('month', Expense.payment_date) == current_month,
            extract('year', Expense.payment_date) == current_year,
            Expense.is_paid == True,
            ExpenseCategory.name != TRANSFER_CATEGORY_NAME
        )
    )
    monthly_paid_expenses = float(monthly_paid_expenses_result)

    monthly_pending_expenses_result = db.session.scalar(
        db.select(func.coalesce(func.sum(Expense.amount), Decimal(0.00)))
        .join(Expense.category)
        .where(
            Expense.user_id == current_user.id,
            extract('month', Expense.due_date) == current_month,
            extract('year', Expense.due_date) == current_year,
            Expense.is_paid == False,
            ExpenseCategory.name != TRANSFER_CATEGORY_NAME
        )
    )
    monthly_pending_expenses = float(monthly_pending_expenses_result)

    revenue_chart_query = db.session.execute(
        db.select(RevenueCategory.name, func.coalesce(func.sum(RevenueTransaction.amount), Decimal(0)))
        .join(RevenueTransaction, RevenueTransaction.category_id == RevenueCategory.id)
        .where(
            RevenueTransaction.user_id == current_user.id, 
            RevenueTransaction.is_received == True, 
            RevenueCategory.name != TRANSFER_CATEGORY_NAME
        )
        .group_by(RevenueCategory.name)
        .order_by(func.sum(RevenueTransaction.amount).desc())
    ).all()
    
    pie_revenue_labels = [row[0] for row in revenue_chart_query if row[1] > 0]
    pie_revenue_data = [float(row[1]) for row in revenue_chart_query if row[1] > 0]
    
    expense_chart_query = db.session.execute(
        db.select(ExpenseCategory.name, func.coalesce(func.sum(Expense.amount), Decimal(0)))
        .join(Expense, Expense.category_id == ExpenseCategory.id)
        .where(
            Expense.user_id == current_user.id, 
            Expense.is_paid == True, 
            ExpenseCategory.name != TRANSFER_CATEGORY_NAME
        )
        .group_by(ExpenseCategory.name)
        .order_by(func.sum(Expense.amount).desc())
    ).all()
    
    pie_expense_labels = [row[0] for row in expense_chart_query if row[1] > 0]
    pie_expense_data = [float(row[1]) for row in expense_chart_query if row[1] > 0]

    receivable_revenues = db.session.execute(
        db.select(RevenueTransaction)
        .join(RevenueTransaction.category)
        .where(
            RevenueTransaction.user_id == current_user.id,
            RevenueTransaction.is_received == False,
            RevenueCategory.name != TRANSFER_CATEGORY_NAME
        )
        .order_by(RevenueTransaction.due_date.asc())
        .limit(5)
    ).scalars().all()
    
    pending_expenses = db.session.execute(
        db.select(Expense)
        .join(Expense.category)
        .where(
            Expense.user_id == current_user.id,
            Expense.is_paid == False,
            ExpenseCategory.name != TRANSFER_CATEGORY_NAME
        )
        .order_by(Expense.due_date.asc())
        .limit(5)
    ).scalars().all()

    dates = [today - timedelta(days=x*30) for x in range(5, -1, -1)]
    chart_labels = [d.strftime('%b') for d in dates]
    
    chart_receitas = [] 
    chart_despesas = [] 

    for d in dates:
        rec_result = db.session.scalar(
            db.select(func.coalesce(func.sum(RevenueTransaction.amount), Decimal(0)))
            .join(RevenueTransaction.category)
            .where(
                RevenueTransaction.user_id == current_user.id,
                extract('month', RevenueTransaction.receipt_date) == d.month,
                extract('year', RevenueTransaction.receipt_date) == d.year,
                RevenueTransaction.is_received == True,
                RevenueCategory.name != TRANSFER_CATEGORY_NAME
            )
        )
        desp_result = db.session.scalar(
            db.select(func.coalesce(func.sum(Expense.amount), Decimal(0)))
            .join(Expense.category)
            .where(
                Expense.user_id == current_user.id,
                extract('month', Expense.payment_date) == d.month,
                extract('year', Expense.payment_date) == d.year,
                Expense.is_paid == True,
                ExpenseCategory.name != TRANSFER_CATEGORY_NAME
            )
        )
        chart_receitas.append(float(rec_result))
        chart_despesas.append(float(desp_result))

    predicted_balance = total_balance + Decimal(monthly_receivable_revenue) - Decimal(monthly_pending_expenses)
        
    context = {
        'total_balance': total_balance,
        'predicted_balance': predicted_balance,
        'monthly_received_revenue': monthly_received_revenue, 
        'monthly_receivable_revenue': monthly_receivable_revenue, 
        'monthly_paid_expenses': monthly_paid_expenses, 
        'monthly_pending_expenses': monthly_pending_expenses, 
        
        'pie_revenue_labels': pie_revenue_labels,
        'pie_revenue_data': pie_revenue_data,
        'pie_expense_labels': pie_expense_labels,
        'pie_expense_data': pie_expense_data,
        
        'receivable_revenues': receivable_revenues,
        'pending_expenses': pending_expenses,
        'now_date': today.date(),
        
        'chart_labels': chart_labels,
        'chart_receitas': chart_receitas,
        'chart_despesas': chart_despesas,

        'is_active': True,
        'title': 'Dashboard'
    }

    return render_template('main/dashboard.html', **context, **footer)

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
