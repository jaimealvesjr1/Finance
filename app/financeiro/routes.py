from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.exceptions import abort
from flask_login import login_required, current_user
from app.extensions import db
from .models import Wallet, RevenueCategory, RevenueTransaction, ExpenseCategory, Expense, Transfer
from .forms import WalletForm, RevenueCategoryForm, RevenueTransactionForm, ExpenseCategoryForm, ExpenseForm, TransferForm
from .services import FinanceService
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
    transfers = Transfer.query.filter_by(user_id=current_user.id).order_by(Transfer.date.desc()).limit(10).all()
    
    return render_template('financeiro/wallets.html', 
                           wallets=wallets, 
                           form=form, 
                           form_transfer=form_transfer,
                           transfers=transfers,
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
            new_transfer = Transfer(
                amount=amount,
                source_wallet_id=source_wallet.id,
                target_wallet_id=target_wallet.id,
                user_id=current_user.id
            )
            db.session.add(new_transfer)

            db.session.commit()
            flash(f'Transferência de {source_wallet.name} para {target_wallet.name} realizada com sucesso!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao realizar a transferência: {e}', 'danger')
            
    else:
        flash_form_errors(form)
    
    return redirect(url_for('financeiro.wallets'))

@financeiro_bp.route('/transferencia/desfazer/<int:transfer_id>', methods=['POST'])
@login_required
def undo_transfer(transfer_id):
    transfer = db.get_or_404(Transfer, transfer_id)
    if transfer.user_id != current_user.id:
        abort(403)
        
    try:
        details = f"Valor: {transfer.amount} | De: {transfer.source_wallet.name} | Para: {transfer.target_wallet.name}"
        FinanceService.log_action(current_user.id, 'DELETE', transfer, details)
        
        db.session.delete(transfer)
        db.session.commit()
        
        flash(f'Transferência desfeita com sucesso! Ação registada no log.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao desfazer a transferência: {e}', 'danger')
        
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
    wallet = db.get_or_404(Wallet, wallet_id)
    if wallet.user_id != current_user.id:
        abort(403)
    
    form = WalletForm()
    
    if form.name.data:
        wallet.name = form.name.data
        db.session.commit()
        flash('Nome da Carteira atualizado com sucesso!', 'success')
    else:
        flash_form_errors(form)

    return redirect(url_for('financeiro.wallets'))

@financeiro_bp.route('/carteiras/editar-saldo-inicial/<int:wallet_id>', methods=['POST'])
@login_required
def manage_initial_balance(wallet_id):
    wallet = db.get_or_404(Wallet, wallet_id)
    if wallet.user_id != current_user.id:
        abort(403)
        
    try:
        new_balance = request.form.get('new_initial_balance', type=Decimal)
        
        if new_balance is None:
            flash('Novo saldo inicial inválido.', 'danger')
            return redirect(url_for('financeiro.wallets'))

        old_balance = wallet.initial_balance
        
        wallet.initial_balance = new_balance
        db.session.commit()
        
        flash(f'Saldo inicial da carteira {wallet.name} alterado de {old_balance:.2f} para {new_balance:.2f} com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar o saldo inicial: {e}', 'danger')
        
    return redirect(url_for('financeiro.wallets'))

@financeiro_bp.route('carteiras/delete/<int:wallet_id>', methods=['POST'])
@login_required
def delete_wallet(wallet_id):
    wallet = db.get_or_404(Wallet, wallet_id)
    if wallet.user_id != current_user.id:
        abort(403)
        
    if wallet.transactions.count() > 0 or wallet.expenses.count() > 0:
        flash('Não é possível excluir a carteira com transações ligadas a ela.', 'danger')
        return redirect(url_for('financeiro.wallets'))
    
    try:
        details = f"Nome: {wallet.name} | Saldo Inicial: {wallet.initial_balance}"
        FinanceService.log_action(current_user.id, 'DELETE', wallet, details)
        
        db.session.delete(wallet)
        db.session.commit()
        flash('Carteira excluída com sucesso!', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')

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
        flash('Não é possível excluir a categoria com transações ligadas a ela.', 'danger')
        return redirect(url_for('financeiro.revenue_categories'))
    
    try:
        FinanceService.log_action(current_user.id, 'DELETE', category, f"Nome: {category.name}")
        
        db.session.delete(category)
        db.session.commit()
        flash('Categoria de Receita excluída com sucesso!', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')

    return redirect(url_for('financeiro.categories_config'))
    
@financeiro_bp.route('/configuracao-despesa')
@login_required
def expense_config():
    return redirect(url_for('financeiro.categories_config'))

@financeiro_bp.route('/configuracao-categorias')
@login_required
def categories_config():
    categories = RevenueCategory.query.filter_by(user_id=current_user.id).order_by(RevenueCategory.name).all()

    expense_categories = ExpenseCategory.query.filter_by(user_id=current_user.id).order_by(ExpenseCategory.name).all()

    form_revenue = RevenueCategoryForm()
    form_expense = ExpenseCategoryForm()

    return render_template('financeiro/categories_config.html',
                           categories=categories,
                           expense_categories=expense_categories,
                           form_revenue=form_revenue,
                           form_expense=form_expense,
                           title='Configuração de Categorias',
                           **footer)

@financeiro_bp.route('/configuracao-despesa/add', methods=['POST'])
@login_required
def add_expense_category():
    form = ExpenseCategoryForm()
    if form.validate_on_submit():
        category = ExpenseCategory(
            name=form.name.data,
            user_id=current_user.id
        )
        db.session.add(category)
        db.session.commit()
        flash('Categoria de Despesa adicionada com sucesso!', 'success')
    else:
        flash_form_errors(form)
    return redirect(url_for('financeiro.categories_config'))

@financeiro_bp.route('/configuracao-despesa/manage/<int:category_id>', methods=['POST'])
@login_required
def manage_expense_category(category_id):
    form = ExpenseCategoryForm()
    category = db.get_or_404(ExpenseCategory, category_id)

    if category.user_id != current_user.id:
        abort(403)

    if form.validate_on_submit():
        category.name = form.name.data
        db.session.commit()
        flash('Categoria de Despesa atualizada com sucesso!', 'success')
    else:
        flash_form_errors(form)
    
    return redirect(url_for('financeiro.categories_config'))

@financeiro_bp.route('/configuracao-despesa/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_expense_category(category_id):
    category = db.get_or_404(ExpenseCategory, category_id)
    if category.user_id != current_user.id:
        abort(403)
        
    if category.expenses.count() > 0:
        flash('Não é possível excluir a categoria com despesas ligadas a ela.', 'danger')
        return redirect(url_for('financeiro.categories_config'))
        
    try:
        FinanceService.log_action(current_user.id, 'DELETE', category, f"Nome: {category.name}")
        
        db.session.delete(category)
        db.session.commit()
        flash('Categoria de Despesa excluída com sucesso!', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
        
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

    desc_filter = request.args.get('desc_filter')
    cat_filter_id = request.args.get('category_filter', type=int)
    wallet_filter_id = request.args.get('wallet_filter', type=int)
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')

    if desc_filter:
        filters.append(RevenueTransaction.description.ilike(f'%{desc_filter}%'))
    
    if cat_filter_id:
        filters.append(RevenueTransaction.category_id == cat_filter_id)

    if wallet_filter_id:
        filters.append(RevenueTransaction.wallet_id == wallet_filter_id)
        
    if date_start:
        filters.append(RevenueTransaction.date >= datetime.strptime(date_start, '%Y-%m-%d').date())
        
    if date_end:
        filters.append(RevenueTransaction.date <= datetime.strptime(date_end, '%Y-%m-%d').date()) 
    
    if filters:
        query = base_query.filter(and_(*filters))
    else:
        query = base_query

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
    
    receivable_revenues = query.filter_by(is_received=False).order_by(RevenueTransaction.due_date.asc()).all()
    received_pagination = query.filter_by(is_received=True).order_by(RevenueTransaction.receipt_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    received_revenues = received_pagination.items
    
    form = RevenueTransactionForm() 
    
    revenue_category_choices = [(c.id, c.name) for c in current_user.categories.all()] 
    
    wallets = Wallet.query.filter_by(user_id=current_user.id).order_by(Wallet.name).all()
    wallet_choices = [(w.id, w.name) for w in wallets]

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
                           wallet_filter_id=wallet_filter_id,
                           date_start=date_start,
                           date_end=date_end,
                           revenue_category_choices=revenue_category_choices,
                           wallet_choices=wallet_choices,
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
            # O Service agora cuida de toda a lógica de decisão
            FinanceService.create_revenue_bulk(form, current_user.id)
            flash('Receita registrada com sucesso!', 'success')
            return redirect(url_for('financeiro.revenues'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro técnico ao salvar: {str(e)}', 'danger')
            return redirect(url_for('financeiro.add_revenue'))
    
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
        details = f"Desc: {revenue.description} | Valor: {revenue.amount} | Data: {revenue.date}"
        FinanceService.log_action(current_user.id, 'DELETE', revenue, details)

        db.session.delete(revenue)
        db.session.commit()
        flash('Receita excluída e ação registrada no log.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {e}', 'danger')
        
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
    wallet_filter_id = request.args.get('wallet_filter', type=int)
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')
    
    filters = []

    if desc_filter:
        filters.append(Expense.description.ilike(f'%{desc_filter}%'))
    
    if item_filter_id:
        filters.append(Expense.category_id == item_filter_id)
    
    if wallet_filter_id:
        filters.append(Expense.wallet_id == wallet_filter_id)
        
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

    expense_categories = ExpenseCategory.query.filter_by(user_id=current_user.id) \
                                     .order_by(ExpenseCategory.name) \
                                     .all()
    expense_category_choices = [(category.id, category.name) for category in expense_categories]

    wallets = Wallet.query.filter_by(user_id=current_user.id).order_by(Wallet.name).all()
    wallet_choices = [(w.id, w.name) for w in wallets]
    
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
                           expense_item_choices=expense_category_choices,
                           desc_filter=desc_filter,
                           item_filter_id=item_filter_id,
                           wallet_filter_id=wallet_filter_id,
                           recurrency_filter=recurrency_filter,
                           date_start=date_start,
                           date_end=date_end,
                           wallet_choices=wallet_choices,
                           **footer)

@financeiro_bp.route('/despesas/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    form = ExpenseForm()
    
    if not current_user.wallets.first():
        flash('Adicione uma Carteira antes de registrar uma Despesa!', 'warning')
        return redirect(url_for('financeiro.wallets'))
    if not ExpenseCategory.query.filter_by(user_id=current_user.id).first():
        flash('Configure Categorias de Despesa primeiro!', 'warning')
        return redirect(url_for('financeiro.expense_config'))
        
    if form.validate_on_submit():
        try:
            FinanceService.create_expense_bulk(form, current_user.id)
            flash('Despesa registrada com sucesso!', 'success')
            return redirect(url_for('financeiro.expenses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro técnico: {str(e)}', 'danger')
            return redirect(url_for('financeiro.add_expense'))
    
    if request.method == 'GET' and not form.status.data:
        form.status.data = 'pending'

    return render_template('financeiro/expense_form.html', form=form, title='Nova Despesa', is_edit=False, **footer)

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
        form.item.data = expense.category 
        form.wallet.data = expense.wallet

    if form.validate_on_submit():
        is_paid_new = (form.status.data == 'paid')
        
        expense.description = form.description.data
        expense.amount = form.amount.data
        expense.date = form.date.data
        expense.due_date = form.due_date.data
        expense.category_id = form.item.data.id
        expense.wallet_id = form.wallet.data.id
        
        if is_paid_new:
            expense.is_paid = True
            expense.payment_date = datetime.combine(form.payment_date.data, datetime.min.time()) if form.payment_date.data else datetime.utcnow()
        else:
            expense.is_paid = False
            expense.payment_date = None
        
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
        details = f"Desc: {expense.description} | Valor: {expense.amount} | Vencimento: {expense.due_date}"
        FinanceService.log_action(current_user.id, 'DELETE', expense, details)

        db.session.delete(expense)
        db.session.commit()
        flash('Despesa excluída e a ação foi registada no log de auditoria.', 'info')
    
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

@financeiro_bp.route('/receitas/bulk', methods=['POST'])
@login_required
def bulk_action_revenues():
    action = request.form.get('action_type')
    ids = request.form.getlist('selected_ids')
    
    if not ids:
        flash('Nenhum item selecionado.', 'warning')
        return redirect(url_for('financeiro.revenues'))
    
    # Filtra transações pelos IDs enviados E garante que pertencem ao usuário atual (segurança)
    revenues = RevenueTransaction.query.filter(
        RevenueTransaction.id.in_(ids), 
        RevenueTransaction.user_id == current_user.id
    ).all()
    
    count = 0
    try:
        if action == 'delete':
            count = len(revenues)
            for rev in revenues:
                db.session.delete(rev)
            flash(f'{count} receitas excluídas com sucesso.', 'success')
            
        elif action == 'receive':
            for rev in revenues:
                if not rev.is_received:
                    rev.is_received = True
                    # Define a data de recebimento como agora, se não houver
                    if not rev.receipt_date:
                        rev.receipt_date = datetime.utcnow()
                    count += 1
            flash(f'{count} receitas marcadas como recebidas.', 'success')
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Erro na ação em massa: {e}', 'danger')
        
    return redirect(url_for('financeiro.revenues'))

@financeiro_bp.route('/despesas/bulk', methods=['POST'])
@login_required
def bulk_action_expenses():
    action = request.form.get('action_type')
    ids = request.form.getlist('selected_ids')
    
    if not ids:
        flash('Nenhum item selecionado.', 'warning')
        return redirect(url_for('financeiro.expenses'))
    
    expenses = Expense.query.filter(
        Expense.id.in_(ids), 
        Expense.user_id == current_user.id
    ).all()
    
    count = 0
    try:
        if action == 'delete':
            count = len(expenses)
            for exp in expenses:
                db.session.delete(exp)
            flash(f'{count} despesas excluídas com sucesso.', 'success')
            
        elif action == 'pay':
            for exp in expenses:
                if not exp.is_paid:
                    exp.is_paid = True
                    # Define data de pagamento como agora, se não houver
                    if not exp.payment_date:
                        exp.payment_date = datetime.utcnow()
                    count += 1
            flash(f'{count} despesas marcadas como pagas.', 'success')
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Erro na ação em massa: {e}', 'danger')
        
    return redirect(url_for('financeiro.expenses'))
