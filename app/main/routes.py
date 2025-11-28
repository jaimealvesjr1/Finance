from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.financeiro.models import Transaction
from app.extensions import db
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from config import Config

main_bp = Blueprint('main', __name__, template_folder='templates')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}

@main_bp.route('/')
@login_required
def index():
    """Página inicial/Dashboard com resumo financeiro e gráficos."""
    
    # 1. Definições de Data (CRÍTICO: Definir isto no topo)
    today = datetime.now()
    current_month = today.month
    current_year = today.year

    # 2. Saldo Total (Soma dos saldos das carteiras)
    total_balance = sum(wallet.current_balance for wallet in current_user.wallets)

    # 3. Filtro base para o mês atual (Usa as variáveis definidas no passo 1)
    monthly_filter = [
        Transaction.user_id == current_user.id,
        extract('month', Transaction.date) == current_month,
        extract('year', Transaction.date) == current_year
    ]

    # 4. KPI: Receitas do Mês
    monthly_income_result = db.session.scalar(
        db.select(func.coalesce(func.sum(Transaction.amount), 0.00)).where(
            *monthly_filter,
            Transaction.type == 'R'
        )
    )
    monthly_income = float(monthly_income_result)

    # 5. KPI: Despesas do Mês
    monthly_expenses_result = db.session.scalar(
        db.select(func.coalesce(func.sum(Transaction.amount), 0.00)).where(
            *monthly_filter,
            Transaction.type == 'D'
        )
    )
    monthly_expenses = float(monthly_expenses_result)

    # 6. Tabela: Últimas Transações
    latest_transactions = Transaction.query.filter_by(user_id=current_user.id) \
                                           .filter_by(is_recurrent=False) \
                                           .order_by(Transaction.date.desc()) \
                                           .limit(5) \
                                           .all()

    # 7. Gráfico: Dados dos Últimos 6 meses
    # Gera os últimos 6 meses a partir de hoje
    dates = [today - timedelta(days=x*30) for x in range(5, -1, -1)]
    chart_labels = [d.strftime('%b') for d in dates] # Ex: Jan, Fev...
    
    chart_receitas = []
    chart_despesas = []

    for d in dates:
        # Filtra receitas do mês/ano específico do loop
        rec = db.session.scalar(
            db.select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == current_user.id,
                extract('month', Transaction.date) == d.month,
                extract('year', Transaction.date) == d.year,
                Transaction.type == 'R'
            )
        )
        # Filtra despesas
        desp = db.session.scalar(
            db.select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == current_user.id,
                extract('month', Transaction.date) == d.month,
                extract('year', Transaction.date) == d.year,
                Transaction.type == 'D'
            )
        )
        chart_receitas.append(float(rec))
        chart_despesas.append(float(desp))

    # 8. Preparar Contexto para o Template
    context = {
        'total_balance': total_balance,
        'latest_transactions': latest_transactions,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'chart_labels': chart_labels,     # Novo
        'chart_receitas': chart_receitas, # Novo
        'chart_despesas': chart_despesas, # Novo
        'title': 'Dashboard'
    }

    return render_template('main/dashboard.html', **context, **footer)
