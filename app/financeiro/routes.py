from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.exceptions import abort
from flask_login import login_required, current_user
from app.extensions import db
from .models import Wallet, RevenueCategory, RevenueTransaction, ExpenseGroup, ExpenseItem, Expense 
from .forms import WalletForm, RevenueCategoryForm, RevenueTransactionForm, ExpenseGroupForm, ExpenseItemForm, ExpenseForm, TransferForm
from config import Config
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_, extract
from decimal import Decimal
from dateutil.relativedelta import relativedelta

financeiro_bp = Blueprint('financeiro', __name__, template_folder='templates', url_prefix='/financeiro')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}

def flash_form_errors(form):
    for field_name, errors in form.errors.items():
        for error in errors:
            field_obj = getattr(form, field_name, None)
            field_label = field_obj.label.text if field_obj and hasattr(field_obj, 'label') else field_name
            flash(f"Erro no campo '{field_label}': {error}", 'danger')

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

@financeiro_bp.route('/carteiras')
@login_required
def wallets():
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    form = WalletForm()
    form_transfer = TransferForm()
    return render_template('financeiro/wallets.html', 
                           wallets=wallets, 
                           form=form, 
                           form_transfer=form_transfer,
                           title='Minhas Carteiras', 
                           **footer)

@financeiro_bp.route('/transferencia', methods=['POST'])
@login_required
def transfer():
    form = TransferForm()
    
    form.source_wallet.query_factory = lambda: Wallet.query.filter_by(user_id=current_user.id).all()
    form.target_wallet.query_factory = lambda: Wallet.query.filter_by(user_id=current_user.id).all()

    if form.validate_on_submit():
        amount = form.amount.data
        source_wallet = form.source_wallet.data
        target_wallet = form.target_wallet.data
        
        try:
            source_wallet.initial_balance -= amount
            target_wallet.initial_balance += amount

            db.session.commit()
            flash(f'Transferência de {source_wallet.name} para {target_wallet.name} realizada com sucesso!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao realizar a transferência: {e}', 'danger')
            
    else:
        flash_form_errors(form)
    
    return redirect(url_for('financeiro.wallets'))

@financeiro_bp.route('/carteiras/add', methods=['POST'])
@login_required
def add_wallet():
    form = WalletForm()
    if form.validate_on_submit():
        wallet = Wallet(
            name=form.name.data,
            initial_balance=form.initial_balance.data,
            user_id=current_user.id
        )
        db.session.add(wallet)
        db.session.commit()
        flash('Carteira adicionada com sucesso!', 'success')
    else:
        flash_form_errors(form)
    
    return redirect(url_for('financeiro.wallets'))

@financeiro_bp.route('/carteiras/manage', defaults={'wallet_id': None}, methods=['POST'])
@financeiro_bp.route('/carteiras/manage/<int:wallet_id>', methods=['POST'])
@login_required
def manage_wallet(wallet_id):
    """Processa a adição (sem ID) ou edição (com ID) de uma carteira."""
    form = WalletForm()

    if form.validate_on_submit():
        if wallet_id is None:
            wallet = Wallet(
                name=form.name.data,
                initial_balance=form.initial_balance.data,
                user_id=current_user.id)
            db.session.add(wallet)
            flash('Carteira adicionada com sucesso!', 'success')
        else:
            wallet = db.get_or_404(Wallet, wallet_id)
            if wallet.user_id != current_user.id:
                abort(403)
            # CORREÇÃO: Atribuição correta
            wallet.name = form.name.data
            wallet.initial_balance = form.initial_balance.data 
            flash('Carteira atualizada com sucesso!', 'success')
        db.session.commit()
    else:
        flash_form_errors(form)

    return redirect(url_for('financeiro.wallets'))

@financeiro_bp.route('carteiras/delete/<int:wallet_id>', methods=['POST'])
@login_required
def delete_wallet(wallet_id):
    """Exclui uma carteira, mas apenas se não houver receitas OU despesas ligadas a ela."""
    wallet = db.get_or_404(Wallet, wallet_id)
    
    if wallet.user_id != current_user.id:
        abort(403)
        
    # ATUALIZAÇÃO CRÍTICA: Checar RevenueTransaction e Expense
    if wallet.transactions.count() > 0 or wallet.expenses.count() > 0:
        flash('Não é possível excluir a carteira, pois há transações (receitas ou despesas) ligadas a ela.', 'danger')
        return redirect(url_for('financeiro.wallets'))
    
    db.session.delete(wallet)
    db.session.commit()
    flash('Carteira excluída com sucesso!', 'info')

    return redirect(url_for('financeiro.wallets'))

@financeiro_bp.route('/categorias-receita')
@login_required
def revenue_categories():
    return redirect(url_for('financeiro.categories_config'))

@financeiro_bp.route('/categorias-receita/add', methods=['POST'])
@login_required
def add_revenue_category():
    form = RevenueCategoryForm()
    if form.validate_on_submit():
        category = RevenueCategory(
            name=form.name.data,
            type='R',
            user_id=current_user.id
        )
        db.session.add(category)
        db.session.commit()
        flash('Categoria de Receita adicionada com sucesso!', 'success')
    else:
        flash_form_errors(form)
    
    return redirect(url_for('financeiro.categories_config'))

@financeiro_bp.route('/categorias-receita/manage', defaults={'category_id': None}, methods=['POST'])
@financeiro_bp.route('/categorias-receita/manage/<int:category_id>', methods=['POST'])
@login_required
def manage_revenue_category(category_id):
    form = RevenueCategoryForm()

    if form.validate_on_submit():
        if category_id is None:
            category = RevenueCategory(
                name=form.name.data,
                type='R',
                user_id=current_user.id)
            db.session.add(category)
            flash('Categoria de Receita adicionada com sucesso!', 'success')
        else:
            category = db.get_or_404(RevenueCategory, category_id)
            if category.user_id != current_user.id:
                abort(403)
            category.name = form.name.data
            category.type = 'R'
            flash('Categoria de Receita atualizada com sucesso!', 'success')
        db.session.commit()
    else:
        flash_form_errors(form)
    
    return redirect(url_for('financeiro.revenue_categories'))

@financeiro_bp.route('categorias-receita/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_revenue_category(category_id):
    category = db.get_or_404(RevenueCategory, category_id)

    if category.user_id != current_user.id:
        abort(403)
        
    if category.transactions.count() > 0:
        flash('Não é possivel excluir a categoria de Receita, pois há transações ligadas a ela.', 'danger')
        return redirect(url_for('financeiro.revenue_categories'))
    
    db.session.delete(category)
    db.session.commit()
    flash('Categoria de Receita excluída com sucesso!', 'info')

    return redirect(url_for('financeiro.categories_config'))
    
@financeiro_bp.route('/configuracao-despesa')
@login_required
def expense_config():
    return redirect(url_for('financeiro.categories_config'))

@financeiro_bp.route('/configuracao-categorias')
@login_required
def categories_config():
    categories = RevenueCategory.query.filter_by(user_id=current_user.id).order_by(RevenueCategory.name).all()

    groups = ExpenseGroup.query.filter_by(user_id=current_user.id).order_by(ExpenseGroup.name).all()
    items = ExpenseItem.query.join(ExpenseGroup).filter(ExpenseItem.user_id == current_user.id).order_by(ExpenseGroup.name, ExpenseItem.name).all()

    form_revenue = RevenueCategoryForm()
    form_group = ExpenseGroupForm()
    form_item = ExpenseItemForm()
    
    return render_template('financeiro/categories_config.html',
                           categories=categories,
                           groups=groups,
                           items=items,
                           form_revenue=form_revenue,
                           form_group=form_group,
                           form_item=form_item,
                           title='Configuração de Categorias',
                           **footer)

@financeiro_bp.route('/configuracao-despesa/group/add', methods=['POST'])
@login_required
def add_expense_group():
    form = ExpenseGroupForm()
    if form.validate_on_submit():
        group = ExpenseGroup(
            name=form.name.data,
            user_id=current_user.id
        )
        db.session.add(group)
        db.session.commit()
        flash('Grupo de Despesa adicionado com sucesso!', 'success')
    else:
        flash_form_errors(form)
    return redirect(url_for('financeiro.categories_config'))

@financeiro_bp.route('/configuracao-despesa/item/add', methods=['POST'])
@login_required
def add_expense_item():
    form = ExpenseItemForm()
    form.group.query_factory = lambda: ExpenseGroup.query.filter_by(user_id=current_user.id).order_by(ExpenseGroup.name).all()

    if form.validate_on_submit():
        item = ExpenseItem(
            name=form.name.data,
            group_id=form.group.data.id,
            user_id=current_user.id
        )
        db.session.add(item)
        db.session.commit()
        flash('Item de Despesa adicionado com sucesso!', 'success')
    else:
        flash_form_errors(form)
    return redirect(url_for('financeiro.categories_config'))

@financeiro_bp.route('/configuracao-despesa/group/delete/<int:group_id>', methods=['POST'])
@login_required
def delete_expense_group(group_id):
    group = db.get_or_404(ExpenseGroup, group_id)
    if group.user_id != current_user.id:
        abort(403)
    if group.items.count() > 0:
        flash('Não é possível excluir o grupo, pois há itens de despesa ligados a ele.', 'danger')
        return redirect(url_for('financeiro.expense_config'))
    
    db.session.delete(group)
    db.session.commit()
    flash('Grupo de Despesa excluído com sucesso!', 'info')
    return redirect(url_for('financeiro.categories_config'))

@financeiro_bp.route('/configuracao-despesa/item/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_expense_item(item_id):
    item = db.get_or_404(ExpenseItem, item_id)
    if item.user_id != current_user.id:
        abort(403)
    if item.expenses.count() > 0:
        flash('Não é possível excluir o item, pois há despesas ligadas a ele.', 'danger')
        return redirect(url_for('financeiro.expense_config'))
        
    db.session.delete(item)
    db.session.commit()
    flash('Item de Despesa excluído com sucesso!', 'info')
    return redirect(url_for('financeiro.categories_config'))

@financeiro_bp.route('/transacoes')
@login_required
def transactions():
    return redirect(url_for('financeiro.expenses')) 

@financeiro_bp.route('/transacoes/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    return redirect(url_for('financeiro.add_revenue'))

@financeiro_bp.route('/transacoes/edit/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    return redirect(url_for('financeiro.edit_revenue', revenue_id=transaction_id))

@financeiro_bp.route('/transacoes/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    return redirect(url_for('financeiro.delete_revenue', revenue_id=transaction_id))


@financeiro_bp.route('/receitas')
@login_required
def revenues():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    now_date = date.today()
    base_query = RevenueTransaction.query.filter_by(user_id=current_user.id)
    filters = []

    # --- Processamento de Filtros ---
    desc_filter = request.args.get('desc_filter')
    cat_filter_id = request.args.get('category_filter', type=int)
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')

    if desc_filter:
        filters.append(RevenueTransaction.description.ilike(f'%{desc_filter}%'))
    
    if cat_filter_id:
        filters.append(RevenueTransaction.category_id == cat_filter_id)
        
    if date_start:
        filters.append(RevenueTransaction.date >= datetime.strptime(date_start, '%Y-%m-%d').date())
        
    if date_end:
        filters.append(RevenueTransaction.date <= datetime.strptime(date_end, '%Y-%m-%d').date()) 
    
    if filters:
        query = base_query.filter(and_(*filters))
    else:
        query = base_query

    # --- CÁLCULO DE TOTAIS NÃO PAGINADOS ---
    total_received_amount = db.session.scalar(
        db.select(func.coalesce(func.sum(RevenueTransaction.amount), Decimal(0))).where(
            RevenueTransaction.user_id == current_user.id, RevenueTransaction.is_received == True
        ).filter(and_(*filters))
    )
    total_received_amount = total_received_amount if total_received_amount is not None else Decimal(0)

    total_receivable_amount = db.session.scalar(
        db.select(func.coalesce(func.sum(RevenueTransaction.amount), Decimal(0))).where(
            RevenueTransaction.user_id == current_user.id, RevenueTransaction.is_received == False
        ).filter(and_(*filters))
    )
    total_receivable_amount = total_receivable_amount if total_receivable_amount is not None else Decimal(0)
    
    # --- Paginação e Listas ---
    
    receivable_revenues = query.filter_by(is_received=False).order_by(RevenueTransaction.due_date.asc()).all()
    received_pagination = query.filter_by(is_received=True).order_by(RevenueTransaction.receipt_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    received_revenues = received_pagination.items
    
    form = RevenueTransactionForm() 
    category_choices = [(c.id, c.name) for c in current_user.categories]

    return render_template('financeiro/revenues.html', 
                           received_revenues=received_revenues,
                           receivable_revenues=receivable_revenues,
                           pagination=received_pagination,
                           total_received_amount=total_received_amount,
                           total_receivable_amount=total_receivable_amount,
                           title='Minhas Receitas',
                           now_date=now_date,
                           desc_filter=desc_filter,
                           cat_filter_id=cat_filter_id,
                           date_start=date_start,
                           date_end=date_end,
                           category_choices=category_choices,
                           **footer)

@financeiro_bp.route('/receitas/add', methods=['GET', 'POST'])
@login_required
def add_revenue():
    form = RevenueTransactionForm()
    
    if not current_user.wallets.first():
        flash('Você precisa adicionar pelo menos uma Carteira antes de registrar uma Receita!', 'warning')
        return redirect(url_for('financeiro.wallets'))
    if not current_user.categories.first():
        flash('Você precisa adicionar pelo menos uma Categoria de Receita antes de registrar uma Receita!', 'warning')
        return redirect(url_for('financeiro.revenue_categories'))
        
    if form.validate_on_submit():
        
        try:
            num_repetitions = int(form.num_repetitions.data)
        except ValueError:
            num_repetitions = 0
            
        is_recurrent_flag = form.is_recurrent.data and num_repetitions == 0
        frequency = form.frequency.data
        frequency_for_template = form.frequency.data if is_recurrent_flag else None
        
        if num_repetitions > 0:
            is_received = False
            receipt_date = None
        else:
            is_received = (form.status.data == 'received')
            receipt_date = datetime.combine(form.receipt_date.data, datetime.min.time()) if is_received and form.receipt_date.data else None
            
        revenue = RevenueTransaction(
            description=form.description.data,
            amount=form.amount.data,
            date=form.date.data,
            due_date=form.due_date.data,
            is_received=is_received,
            receipt_date=receipt_date,
            
            is_recurrent=is_recurrent_flag,
            frequency=frequency_for_template,
            
            type='R',
            user_id=current_user.id,
            wallet_id=form.wallet.data.id,
            category_id=form.category.data.id
        )
        db.session.add(revenue)

        if num_repetitions > 0:
            if not frequency or frequency == '':
                 flash('A frequência é obrigatória para repetições em massa.', 'danger')
                 db.session.rollback()
                 return redirect(url_for('financeiro.add_revenue'))
                 
            current_due_date = form.due_date.data
            for _ in range(num_repetitions):
                current_due_date = calculate_next_date(current_due_date, frequency)
                
                new_revenue = RevenueTransaction(
                    description=form.description.data,
                    amount=form.amount.data,
                    date=form.date.data, 
                    due_date=current_due_date,
                    is_received=False, 
                    receipt_date=None, 
                    
                    is_recurrent=False, 
                    frequency=None,
                    
                    type='R',
                    user_id=current_user.id,
                    wallet_id=form.wallet.data.id,
                    category_id=form.category.data.id
                )
                db.session.add(new_revenue)
            
            db.session.commit()
            total_lancamentos = num_repetitions + 1
            msg = f'Receita registrada e mais {num_repetitions} lançamentos futuros criados (Total: {total_lancamentos}).'
            flash(msg, 'success')
            return redirect(url_for('financeiro.revenues'))
        
        db.session.commit()
        
        if is_recurrent_flag:
            msg = 'Receita registrada como template de recorrência contínua (agendada) com sucesso! Ela será repetida automaticamente.'
        else:
            msg = 'Receita registrada como RECEBIDA com sucesso!' if is_received else 'Receita registrada como A RECEBER com sucesso!'
            
        flash(msg, 'success')
        return redirect(url_for('financeiro.revenues'))
    
    if request.method == 'GET':
        if not form.status.data:
            form.status.data = 'pending'
        if not form.date.data:
            form.date.data = date.today()
        if not form.due_date.data:
            form.due_date.data = date.today()
        
    return render_template('financeiro/revenue_form.html', form=form, title='Nova Receita', is_edit=False, transaction_id=None, **footer)

@financeiro_bp.route('/receitas/edit/<int:revenue_id>', methods=['GET', 'POST'])
@login_required
def edit_revenue(revenue_id):
    revenue = db.get_or_404(RevenueTransaction, revenue_id)
    if revenue.user_id != current_user.id: abort(403)
    
    form = RevenueTransactionForm(obj=revenue)
    
    if request.method == 'GET':
        form.status.data = 'received' if revenue.is_received else 'pending'
        form.receipt_date.data = revenue.receipt_date.date() if revenue.receipt_date else None
        
        form.wallet.data = revenue.wallet
        form.category.data = revenue.category

    if form.validate_on_submit():
        is_received_new = (form.status.data == 'received')
        
        revenue.description = form.description.data
        revenue.amount = form.amount.data
        revenue.date = form.date.data
        revenue.due_date = form.due_date.data
        revenue.wallet_id = form.wallet.data.id
        revenue.category_id = form.category.data.id
        revenue.is_recurrent = form.is_recurrent.data
        revenue.frequency = form.frequency.data if form.is_recurrent.data else None
        
        if is_received_new:
            revenue.is_received = True
            revenue.receipt_date = datetime.combine(form.receipt_date.data, datetime.min.time()) if form.receipt_date.data else datetime.utcnow()
        else:
            revenue.is_received = False
            revenue.receipt_date = None
        
        db.session.commit()
        flash('Receita atualizada com sucesso!', 'success')
        return redirect(url_for('financeiro.revenues'))
    
    return render_template('financeiro/revenue_form.html',
                           form=form,
                           title='Editar Receita',
                           is_edit=True,
                           transaction_id=revenue_id, 
                           revenue=revenue,
                           **footer)

@financeiro_bp.route('/receitas/delete/<int:revenue_id>', methods=['POST'])
@login_required
def delete_revenue(revenue_id):
    revenue = db.get_or_404(RevenueTransaction, revenue_id)
    if revenue.user_id != current_user.id: abort(403)
    try:
        db.session.delete(revenue)
        db.session.commit()
        flash('Receita excluída com sucesso!', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir a Receita: {e}', 'danger')
    return redirect(url_for('financeiro.revenues'))

@financeiro_bp.route('/receitas/receive/<int:revenue_id>', methods=['POST'])
@login_required
def mark_as_received(revenue_id):
    revenue = db.get_or_404(RevenueTransaction, revenue_id)
    if revenue.user_id != current_user.id: abort(403)
    if revenue.is_received:
        flash('Esta receita já está marcada como recebida.', 'warning')
        return redirect(url_for('financeiro.revenues'))
        
    revenue.is_received = True
    revenue.receipt_date = datetime.utcnow()
    
    try:
        db.session.commit()
        flash(f'Recebimento de "{revenue.description}" confirmado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao dar baixa no recebimento: {e}', 'danger')

    return redirect(url_for('financeiro.revenues'))

@financeiro_bp.route('/despesas')
@login_required
def expenses():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    now_date = date.today()
    
    base_query = Expense.query.filter_by(user_id=current_user.id)

    desc_filter = request.args.get('desc_filter')
    item_filter_id = request.args.get('item_filter', type=int)
    recurrency_filter = request.args.get('recurrency_filter')
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')
    
    filters = []

    if desc_filter:
        filters.append(Expense.description.ilike(f'%{desc_filter}%'))
    
    if item_filter_id:
        filters.append(Expense.item_id == item_filter_id)
        
    if recurrency_filter and recurrency_filter == 'Isolada':
        filters.append(Expense.is_recurrent == False)
    elif recurrency_filter and recurrency_filter == 'Recorrente':
        filters.append(Expense.is_recurrent == True)
    elif recurrency_filter:
        filters.append(Expense.frequency == recurrency_filter)
        
    if date_start:
        filters.append(Expense.due_date >= datetime.strptime(date_start, '%Y-%m-%d').date())
        
    if date_end:
        filters.append(Expense.due_date <= datetime.strptime(date_end, '%Y-%m-%d').date())

    if filters:
        base_query = base_query.filter(and_(*filters))

    total_paid_query = db.session.scalar(
        db.select(func.coalesce(func.sum(Expense.amount), Decimal(0))).where(
            Expense.user_id == current_user.id,
            Expense.is_paid == True
        )
    )
    total_paid_amount = total_paid_query if total_paid_query is not None else Decimal(0)
    
    total_pending_query = db.session.scalar(
        db.select(func.coalesce(func.sum(Expense.amount), Decimal(0))).where(
            Expense.user_id == current_user.id,
            Expense.is_paid == False
        )
    )
    total_pending_amount = total_pending_query if total_pending_query is not None else Decimal(0)

    pending_expenses = base_query.filter_by(is_paid=False) \
                                    .order_by(Expense.due_date.asc()) \
                                    .all()

    paid_pagination = base_query.filter_by(is_paid=True) \
                                   .order_by(Expense.payment_date.desc()) \
                                   .paginate(page=page, per_page=per_page, error_out=False)
    
    paid_expenses = paid_pagination.items

    expense_items = ExpenseItem.query.filter_by(user_id=current_user.id) \
                                     .order_by(ExpenseItem.name) \
                                     .all()
    expense_item_choices = [(item.id, item.name) for item in expense_items]
    
    form = ExpenseForm()
    frequency_choices = {key: label for key, label in form.frequency.choices if key} 

    return render_template('financeiro/expenses.html',
                           paid_expenses=paid_expenses,
                           pending_expenses=pending_expenses,
                           pagination=paid_pagination,
                           total_paid_amount=total_paid_amount,
                           total_pending_amount=total_pending_amount,
                           frequency_choices=frequency_choices,
                           title='Minhas Despesas', 
                           now_date=now_date,
                           expense_item_choices=expense_item_choices,
                           desc_filter=desc_filter,
                           item_filter_id=item_filter_id,
                           recurrency_filter=recurrency_filter,
                           date_start=date_start,
                           date_end=date_end,
                           **footer)

@financeiro_bp.route('/despesas/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    form = ExpenseForm()
    
    if not current_user.wallets.first():
        flash('Você precisa adicionar pelo menos uma Carteira antes de registrar uma Despesa!', 'warning')
        return redirect(url_for('financeiro.wallets'))
    if not current_user.expense_items.first():
        flash('Você precisa configurar Itens de Despesa antes de registrar uma Despesa!', 'warning')
        return redirect(url_for('financeiro.expense_config'))
        
    if form.validate_on_submit():
        is_paid = (form.status.data == 'paid')
        
        # Lógica para o novo recurso de lançamentos em massa (IML)
        try:
            num_repetitions = int(form.num_repetitions.data)
        except ValueError:
            num_repetitions = 0
            
        frequency = form.frequency.data
        
        # 1. Determina se esta transação será um template CR ou o início de uma IML
        # Se houver repetições IML (num_repetitions > 0), esta transação NÃO deve ser um template de recorrência contínua (CR)
        is_recurrent_flag = form.is_recurrent.data and num_repetitions == 0 
        frequency_for_template = form.frequency.data if is_recurrent_flag else None

        # 1. Cria a primeira (ou única) transação base
        expense = Expense(
            description=form.description.data,
            amount=form.amount.data,
            date=form.date.data,
            due_date=form.due_date.data,
            is_paid=is_paid,
            payment_date=datetime.combine(form.payment_date.data, datetime.min.time()) if is_paid and form.payment_date.data else None,
            
            is_recurrent=is_recurrent_flag,
            frequency=frequency_for_template,
            
            user_id=current_user.id,
            wallet_id=form.wallet.data.id,
            item_id=form.item.data.id
        )
        
        db.session.add(expense)

        # 2. Lançamento em massa de instâncias futuras (se num_repetitions > 0)
        if num_repetitions > 0:
            if not frequency or frequency == '':
                 flash('A frequência é obrigatória para repetições em massa.', 'danger')
                 db.session.rollback()
                 return redirect(url_for('financeiro.add_expense'))
                 
            # A primeira despesa já foi adicionada, agora adicionamos as repetições.
            current_due_date = form.due_date.data
            for _ in range(num_repetitions):
                # Calcula a próxima data de vencimento (a partir da data anterior)
                current_due_date = calculate_next_date(current_due_date, frequency)
                
                # Cria uma nova instância de despesa, sempre A PAGAR (is_paid=False) e NÃO recorrente
                new_expense = Expense(
                    description=form.description.data,
                    amount=form.amount.data,
                    date=form.date.data, # Mantido o date original, mas usei date.today() no outro passo, usar a data de registro do form.
                    due_date=current_due_date,
                    is_paid=False, 
                    payment_date=None, 
                    
                    is_recurrent=False, # Não é um template para o job
                    frequency=None,
                    
                    user_id=current_user.id,
                    wallet_id=form.wallet.data.id,
                    item_id=form.item.data.id
                )
                db.session.add(new_expense)
            
            db.session.commit()
            total_lancamentos = num_repetitions + 1 # Transação inicial + repetições
            msg = f'Despesa registrada e mais {num_repetitions} lançamentos futuros criados (Total: {total_lancamentos}).'
            flash(msg, 'success')
            return redirect(url_for('financeiro.expenses'))
            
        # 3. Lançamento único ou recorrente contínuo (se num_repetitions == 0)
        db.session.commit()
        
        if is_recurrent_flag:
            msg = 'Despesa registrada como template de recorrência contínua (agendada) com sucesso! Ela será repetida automaticamente.'
        else:
            msg = 'Despesa registrada como PAGA com sucesso!' if is_paid else 'Despesa registrada como PENDENTE com sucesso!'
            
        flash(msg, 'success')
        return redirect(url_for('financeiro.expenses'))
    
    if request.method == 'GET' and not form.status.data:
        form.status.data = 'pending'

    return render_template('financeiro/expense_form.html',
                           form=form, 
                           title='Nova Despesa',
                           is_edit=False,
                           expense_id=None, **footer)

@financeiro_bp.route('/despesas/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):    
    expense = db.get_or_404(Expense, expense_id)
    if expense.user_id != current_user.id:
        abort(403)
    form = ExpenseForm(obj=expense)
    
    if request.method == 'GET':
        form.status.data = 'paid' if expense.is_paid else 'pending'
        form.payment_date.data = expense.payment_date.date() if expense.payment_date else None
        
        form.item.data = expense.item
        form.wallet.data = expense.wallet

    if form.validate_on_submit():
        is_paid_new = (form.status.data == 'paid')
        
        expense.description = form.description.data
        expense.amount = form.amount.data
        expense.date = form.date.data
        expense.due_date = form.due_date.data
        expense.item_id = form.item.data.id
        expense.wallet_id = form.wallet.data.id
        
        # Lógica de Status de Pagamento
        if is_paid_new:
            expense.is_paid = True
            # Se for pago, usa a data de pagamento do form, ou a data de competência se vazia.
            expense.payment_date = datetime.combine(form.payment_date.data, datetime.min.time()) if form.payment_date.data else datetime.utcnow()
        else:
            expense.is_paid = False
            expense.payment_date = None
        
        # Lógica de Recorrência
        expense.is_recurrent = form.is_recurrent.data
        expense.frequency = form.frequency.data if form.is_recurrent.data else None
        
        db.session.commit()
        flash('Despesa atualizada com sucesso!', 'success')
        return redirect(url_for('financeiro.expenses'))
        
    
    return render_template('financeiro/expense_form.html',
                           form=form, 
                           title='Editar Despesa',
                           is_edit=True,
                           expense_id=expense_id, **footer)

@financeiro_bp.route('/despesas/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = db.get_or_404(Expense, expense_id)
    
    if expense.user_id != current_user.id:
        abort(403)
        
    try:
        db.session.delete(expense)
        db.session.commit()
        flash('Despesa excluída com sucesso!', 'info')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir a Despesa: {e}', 'danger')
        
    return redirect(url_for('financeiro.expenses'))

@financeiro_bp.route('/despesas/pay/<int:expense_id>', methods=['POST'])
@login_required
def pay_expense(expense_id):
    expense = db.get_or_404(Expense, expense_id)
    
    if expense.user_id != current_user.id:
        abort(403)

    if expense.is_paid:
        flash('Esta despesa já está marcada como paga.', 'warning')
        return redirect(url_for('financeiro.expenses'))
        
    expense.is_paid = True
    expense.payment_date = datetime.utcnow()
    
    try:
        db.session.commit()
        flash(f'Despesa "{expense.description}" paga com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao dar baixa na despesa: {e}', 'danger')

    return redirect(url_for('financeiro.expenses'))
