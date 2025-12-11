from app.extensions import db
from .models import Expense
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import logging

logging.basicConfig(level=logging.INFO)

def calculate_next_date(start_date, frequency):
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
    logging.info("--- Iniciando verificação de despesas recorrentes ---")
    
    recurrent_expenses = Expense.query.filter_by(is_recurrent=True).all()
    
    today = datetime.utcnow().date()
    new_expenses_count = 0

    for template_tx in recurrent_expenses:
        last_ref_date = template_tx.last_launch_date.date() if template_tx.last_launch_date else template_tx.due_date
        frequency = template_tx.frequency
        
        current_date_to_check = last_ref_date
        
        while True:
            next_launch_date = calculate_next_date(current_date_to_check, frequency)
            
            if next_launch_date <= today:
                new_tx = Expense(
                    description=template_tx.description,
                    amount=template_tx.amount,
                    
                    date=date.today(),
                    due_date=next_launch_date,
                    is_paid=False,
                    payment_date=None, 
                    
                    is_recurrent=False, 
                    frequency=None,
                    last_launch_date=None,

                    user_id=template_tx.user_id,
                    wallet_id=template_tx.wallet_id,
                    item_id=template_tx.item_id,
                )
                
                db.session.add(new_tx)
                new_expenses_count += 1
                
                current_date_to_check = next_launch_date 
            else:
                break
        
        if current_date_to_check != last_ref_date:
            template_tx.last_launch_date = datetime(current_date_to_check.year, current_date_to_check.month, current_date_to_check.day)

    
    if new_expenses_count > 0:
        db.session.commit()
        logging.info(f"--- Sucesso: Lançadas {new_expenses_count} novas despesas a pagar. ---")
    else:
        db.session.rollback()
        logging.info("--- Nenhuma despesa recorrente para lançar hoje. ---")
