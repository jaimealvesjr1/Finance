from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.financeiro.models import Wallet, RevenueTransaction, Expense, RevenueCategory, ExpenseItem, ExpenseGroup
from app.extensions import db
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from config import Config
from decimal import Decimal

main_bp = Blueprint('main', __name__, template_folder='templates')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}
TRANSFER_CATEGORY_NAME = 'Transferência' # Constante para filtro de transferência

@main_bp.route('/')
@login_required
def index():
    today = datetime.now()
    current_month = today.month
    current_year = today.year

    # 1. SALDO TOTAL
    total_balance = sum(wallet.current_balance for wallet in current_user.wallets)

    # CÁLCULOS DE VALORES (Executados e Previstos no Mês)
    
    # Receitas Recebidas (Executado) - Exclui Transferências
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
    monthly_received_revenue = float(monthly_received_revenue_result) # CORREÇÃO: Conversão explícita

    # Receitas a Receber (Previsto) - Exclui Transferências
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
    monthly_receivable_revenue = float(monthly_receivable_revenue_result) # CORREÇÃO: Conversão explícita
    
    # Despesas Pagas (Executado) - Exclui Transferências
    monthly_paid_expenses_result = db.session.scalar(
        db.select(func.coalesce(func.sum(Expense.amount), Decimal(0.00)))
        .join(Expense.item) 
        .where(
            Expense.user_id == current_user.id,
            extract('month', Expense.payment_date) == current_month,
            extract('year', Expense.payment_date) == current_year,
            Expense.is_paid == True,
            ExpenseItem.name != TRANSFER_CATEGORY_NAME
        )
    )
    monthly_paid_expenses = float(monthly_paid_expenses_result) # CORREÇÃO: Conversão explícita

    # Despesas a Pagar (Previsto) - Exclui Transferências
    monthly_pending_expenses_result = db.session.scalar(
        db.select(func.coalesce(func.sum(Expense.amount), Decimal(0.00)))
        .join(Expense.item) 
        .where(
            Expense.user_id == current_user.id,
            extract('month', Expense.due_date) == current_month,
            extract('year', Expense.due_date) == current_year,
            Expense.is_paid == False,
            ExpenseItem.name != TRANSFER_CATEGORY_NAME
        )
    )
    monthly_pending_expenses = float(monthly_pending_expenses_result) # CORREÇÃO: Conversão explícita

    # 2. GRÁFICOS DE PIZZA (Receitas Recebidas por Categoria) - Exclui Transferências
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
    # Conversão explícita para float (para Chart.js)
    pie_revenue_data = [float(row[1]) for row in revenue_chart_query if row[1] > 0]
    
    # 2. GRÁFICOS DE PIZZA (Despesas Pagas por Item) - Exclui Transferências
    expense_chart_query = db.session.execute(
        db.select(ExpenseGroup.name, ExpenseItem.name, func.coalesce(func.sum(Expense.amount), Decimal(0)))
        .join(Expense, Expense.item_id == ExpenseItem.id)
        .join(ExpenseItem.group) 
        .where(
            Expense.user_id == current_user.id, 
            Expense.is_paid == True, 
            ExpenseItem.name != TRANSFER_CATEGORY_NAME
        )
        .group_by(ExpenseGroup.name, ExpenseItem.name) 
        .order_by(func.sum(Expense.amount).desc())
    ).all()
    
    pie_expense_labels = [f"{row[0]} > {row[1]}" for row in expense_chart_query if row[2] > 0]
    # Conversão explícita para float (para Chart.js)
    pie_expense_data = [float(row[2]) for row in expense_chart_query if row[2] > 0]

    # 3. LISTAS (Receitas a Receber e Despesas a Pagar) - Exclui Transferências
    
    # Receitas a Receber (Top 5)
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
    
    # Despesas a Pagar (Top 5)
    pending_expenses = db.session.execute(
        db.select(Expense)
        .join(Expense.item)
        .where(
            Expense.user_id == current_user.id,
            Expense.is_paid == False,
            ExpenseItem.name != TRANSFER_CATEGORY_NAME
        )
        .order_by(Expense.due_date.asc())
        .limit(5)
    ).scalars().all()

    # 4. GRÁFICO DE BARRAS MENSAL - Exclui Transferências
    dates = [today - timedelta(days=x*30) for x in range(5, -1, -1)]
    chart_labels = [d.strftime('%b') for d in dates]
    
    chart_receitas = [] 
    chart_despesas = [] 

    for d in dates:
        # Receitas Recebidas no mês (Filtrando por data de RECEBIMENTO e EXCLUINDO TRANSFERÊNCIA)
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
        # Despesas Pagas no mês (Filtrando por data de PAGAMENTO e EXCLUINDO TRANSFERÊNCIA)
        desp_result = db.session.scalar(
            db.select(func.coalesce(func.sum(Expense.amount), Decimal(0)))
            .join(Expense.item)
            .where(
                Expense.user_id == current_user.id,
                extract('month', Expense.payment_date) == d.month,
                extract('year', Expense.payment_date) == d.year,
                Expense.is_paid == True,
                ExpenseItem.name != TRANSFER_CATEGORY_NAME
            )
        )
        chart_receitas.append(float(rec_result))
        chart_despesas.append(float(desp_result))
        
    context = {
        # KPI Cards (Atualizados)
        'total_balance': total_balance,
        'monthly_received_revenue': monthly_received_revenue, 
        'monthly_receivable_revenue': monthly_receivable_revenue, 
        'monthly_paid_expenses': monthly_paid_expenses, 
        'monthly_pending_expenses': monthly_pending_expenses, 
        
        # Pie Charts
        'pie_revenue_labels': pie_revenue_labels,
        'pie_revenue_data': pie_revenue_data,
        'pie_expense_labels': pie_expense_labels,
        'pie_expense_data': pie_expense_data,
        
        # Lists (Novas)
        'receivable_revenues': receivable_revenues,
        'pending_expenses': pending_expenses,
        'now_date': today.date(), # Usado para comparação de datas de vencimento/recebimento
        
        # Bar Chart (6 months)
        'chart_labels': chart_labels,
        'chart_receitas': chart_receitas,
        'chart_despesas': chart_despesas,

        'title': 'Dashboard'
    }

    return render_template('main/dashboard.html', **context, **footer)
