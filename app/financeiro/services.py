from datetime import datetime, date
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from app.extensions import db
from .models import RevenueTransaction, Expense, AuditLog

class FinanceService:
    @staticmethod
    def calculate_next_date(start_date, frequency):
        """Centraliza a lógica de períodos."""
        periods = {
            'daily': relativedelta(days=1),
            'weekly': relativedelta(weeks=1),
            'monthly': relativedelta(months=1),
            'yearly': relativedelta(years=1)
        }
        return start_date + periods.get(frequency, relativedelta(days=0))

    @classmethod
    def create_revenue_bulk(cls, form_data, user_id):
        """Gerencia a criação de múltiplas receitas com integridade."""
        num_repetitions = form_data.num_repetitions.data or 0
        frequency = form_data.frequency.data
        
        # Cria a primeira (ou única)
        revenue = RevenueTransaction(
            description=form_data.description.data,
            amount=form_data.amount.data,
            date=form_data.date.data,
            due_date=form_data.due_date.data,
            is_received=(form_data.status.data == 'received' and num_repetitions == 0),
            user_id=user_id,
            wallet_id=form_data.wallet.data.id,
            category_id=form_data.category.data.id,
            is_recurrent=(form_data.is_recurrent.data and num_repetitions == 0),
            frequency=frequency if (form_data.is_recurrent.data and num_repetitions == 0) else None
        )
        db.session.add(revenue)

        # Lógica de repetição em massa
        if num_repetitions > 0 and frequency:
            current_due = form_data.due_date.data
            for _ in range(num_repetitions):
                current_due = cls.calculate_next_date(current_due, frequency)
                new_rev = RevenueTransaction(
                    description=form_data.description.data,
                    amount=form_data.amount.data,
                    date=form_data.date.data,
                    due_date=current_due,
                    is_received=False,
                    user_id=user_id,
                    wallet_id=form_data.wallet.data.id,
                    category_id=form_data.category.data.id
                )
                db.session.add(new_rev)
        
        db.session.commit()
        return revenue

    @classmethod
    def create_expense_bulk(cls, form_data, user_id):
        num_repetitions = form_data.num_repetitions.data or 0
        frequency = form_data.frequency.data
        is_paid = (form_data.status.data == 'paid')
        
        expense = Expense(
            description=form_data.description.data,
            amount=form_data.amount.data,
            date=form_data.date.data,
            due_date=form_data.due_date.data,
            is_paid=is_paid,
            payment_date=datetime.combine(form_data.payment_date.data, datetime.min.time()) if is_paid and form_data.payment_date.data else None,
            user_id=user_id,
            wallet_id=form_data.wallet.data.id,
            category_id=form_data.item.data.id,
            is_recurrent=(form_data.is_recurrent.data and num_repetitions == 0),
            frequency=frequency if (form_data.is_recurrent.data and num_repetitions == 0) else None
        )
        db.session.add(expense)

        if num_repetitions > 0 and frequency:
            current_due = form_data.due_date.data
            for _ in range(num_repetitions):
                current_due = cls.calculate_next_date(current_due, frequency)
                new_exp = Expense(
                    description=form_data.description.data,
                    amount=form_data.amount.data,
                    date=form_data.date.data,
                    due_date=current_due,
                    is_paid=False,
                    user_id=user_id,
                    wallet_id=form_data.wallet.data.id,
                    category_id=form_data.item.data.id
                )
                db.session.add(new_exp)
        
        db.session.commit()
        return expense
    
    @staticmethod
    def log_action(user_id, action, target_obj, details=None):
        """Registra uma ação no log de auditoria."""
        log = AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_obj.__class__.__name__.upper(),
            target_id=target_obj.id,
            details=details
        )
        db.session.add(log)

    @classmethod
    def process_recurring_item(cls, item, model_class):
        """Lógica central para processar uma única recorrência (Receita ou Despesa)."""
        hoje = date.today()
        
        # Se já foi lançado hoje ou no futuro, ignora para evitar duplicidade
        if item.last_launch_date and item.last_launch_date.date() >= hoje:
            return False

        proxima_data = cls.calculate_next_date(item.due_date, item.frequency)
        
        # Só lança se a próxima data já chegou ou passou
        if proxima_data <= hoje:
            nova_instancia = model_class(
                description=item.description,
                amount=item.amount,
                date=hoje,
                due_date=proxima_data,
                user_id=item.user_id,
                wallet_id=item.wallet_id,
                category_id=item.category_id,
                is_recurrent=False, # A nova instância é um lançamento real, não um template
                type=getattr(item, 'type', None) # Apenas para RevenueTransaction
            )
            
            # Atualiza o template original para a próxima rodada
            item.last_launch_date = datetime.utcnow()
            item.due_date = proxima_data 
            
            db.session.add(nova_instancia)
            cls.log_action(item.user_id, 'AUTO_CREATE', nova_instancia, f"Gerado via recorrência de: {item.id}")
            return True
        return False