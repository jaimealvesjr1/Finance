from app.extensions import db
from .models import Transaction
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

logging.basicConfig(level=logging.INFO)

def calculate_next_date(start_date, frequency):
    """
    Calcula a próxima data de lançamento com base na frequência.
    start_date é um objeto date (sem hora).
    """
    if frequency == 'daily':
        return start_date + relativedelta(days=1)
    elif frequency == 'weekly':
        return start_date + relativedelta(weeks=1)
    elif frequency == 'monthly':
        return start_date + relativedelta(months=1)
    elif frequency == 'yearly':
        return start_date + relativedelta(years=1)
    
    return start_date


def process_recurrent_transactions():
    """
    Verifica transações recorrentes e cria novas ocorrências.
    """
    logging.info("--- Iniciando verificação de transações recorrentes ---")
    
    recurrent_transactions = Transaction.query.filter_by(is_recurrent=True).all()
    
    today = datetime.utcnow().date()
    new_transactions_count = 0

    for template_tx in recurrent_transactions:
        last_ref_date = template_tx.last_launch_date.date() if template_tx.last_launch_date else template_tx.date.date()
        frequency = template_tx.frequency
        
        current_date_to_check = last_ref_date
        
        while True:
            next_launch_date = calculate_next_date(current_date_to_check, frequency)
            
            if next_launch_date <= today:
                new_tx = Transaction(
                    description=template_tx.description,
                    amount=template_tx.amount,
                    date=datetime(next_launch_date.year, next_launch_date.month, next_launch_date.day), 
                    type=template_tx.type,
                    is_recurrent=False, 
                    frequency=None,
                    user_id=template_tx.user_id,
                    wallet_id=template_tx.wallet_id,
                    category_id=template_tx.category_id,
                )
                
                db.session.add(new_tx)
                new_transactions_count += 1
                
                current_date_to_check = next_launch_date 
            else:
                break
        
        if current_date_to_check != last_ref_date:
            template_tx.last_launch_date = datetime(current_date_to_check.year, current_date_to_check.month, current_date_to_check.day)

    
    if new_transactions_count > 0:
        db.session.commit()
        logging.info(f"--- Sucesso: Lançadas {new_transactions_count} novas transações. ---")
    else:
        db.session.rollback()
        logging.info("--- Nenhuma transação recorrente para lançar hoje. ---")
