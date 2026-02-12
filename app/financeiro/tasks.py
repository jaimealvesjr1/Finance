from app.extensions import db
from .models import RevenueTransaction, Expense
from .services import FinanceService

def process_recurrent_transactions():
    """
    Tarefa agendada que percorre templates de recorrência 
    e gera os lançamentos do dia.
    """
    # 1. Processar Receitas Recorrentes
    recurring_revenues = RevenueTransaction.query.filter_by(is_recurrent=True).all()
    for rev in recurring_revenues:
        FinanceService.process_recurring_item(rev, RevenueTransaction)

    # 2. Processar Despesas Recorrentes
    recurring_expenses = Expense.query.filter_by(is_recurrent=True).all()
    for exp in recurring_expenses:
        FinanceService.process_recurring_item(exp, Expense)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Aqui no futuro podemos logar num ficheiro de erros do sistema
        print(f"Erro no processamento de recorrências: {e}")
