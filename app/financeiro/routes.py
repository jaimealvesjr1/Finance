from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.exceptions import abort
from flask_login import login_required, current_user
from app.extensions import db
from .models import Wallet, RevenueCategory, RevenueTransaction, ExpenseGroup, ExpenseItem, Expense 
from .forms import WalletForm, RevenueCategoryForm, RevenueTransactionForm, ExpenseGroupForm, ExpenseItemForm, ExpenseForm
from config import Config
from datetime import datetime, date
from sqlalchemy import func
from decimal import Decimal

financeiro_bp = Blueprint('financeiro', __name__, template_folder='templates', url_prefix='/financeiro')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}

@financeiro_bp.route('/carteiras')
@login_required
def wallets():
    """Lista todas as carteiras do usuário e permite adicionar uma nova."""
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    form = WalletForm()
    return render_template('financeiro/wallets.html', wallets=wallets, form=form, title='Minhas Carteiras', **footer)

@financeiro_bp.route('/carteiras/add', methods=['POST'])
@login_required
def add_wallet():
    """Processa a adição de uma nova carteira."""
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
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{field}': {error}", 'danger')
    
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
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Erro no formulário da Carteira: {error}', 'danger')
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

# ----------------------------------------------------------------------
# 2. Rotas de Categorias de RECEITA (RevenueCategory)
# ----------------------------------------------------------------------
@financeiro_bp.route('/categorias-receita')
@login_required
def revenue_categories():
    """Lista todas as categorias de receita do usuário e permite adicionar uma nova."""
    # Renomeada de categories() para revenue_categories()
    categories = RevenueCategory.query.filter_by(user_id=current_user.id).order_by(RevenueCategory.name).all()
    form = RevenueCategoryForm() # Formulário atualizado
    # Template 'financeiro/categories.html' deve ser editado para remover a lógica 'type'
    return render_template('financeiro/categories.html', categories=categories, form=form, title='Categorias de Receita', **footer)

@financeiro_bp.route('/categorias-receita/add', methods=['POST'])
@login_required
def add_revenue_category():
    """Processa a adição de uma nova categoria de receita."""
    form = RevenueCategoryForm() # Formulário atualizado
    if form.validate_on_submit():
        category = RevenueCategory(
            name=form.name.data,
            type='R', # Força para 'R' (Receita)
            user_id=current_user.id
        )
        db.session.add(category)
        db.session.commit()
        flash('Categoria de Receita adicionada com sucesso!', 'success')
    else:
        flash('Erro ao adicionar categoria de receita. Verifique os dados.', 'danger')
    
    return redirect(url_for('financeiro.revenue_categories'))

@financeiro_bp.route('/categorias-receita/manage', defaults={'category_id': None}, methods=['POST'])
@financeiro_bp.route('/categorias-receita/manage/<int:category_id>', methods=['POST'])
@login_required
def manage_revenue_category(category_id):
    """Processa a adição (sem ID) ou edição (com ID) de uma categoria de receita."""
    form = RevenueCategoryForm() # Formulário atualizado

    if form.validate_on_submit():
        if category_id is None:
            category = RevenueCategory(
                name=form.name.data,
                type='R', # Força para 'R' (Receita)
                user_id=current_user.id)
            db.session.add(category)
            flash('Categoria de Receita adicionada com sucesso!', 'success')
        else:
            category = db.get_or_404(RevenueCategory, category_id)
            if category.user_id != current_user.id:
                abort(403)
            category.name = form.name.data
            category.type = 'R' # Mantém 'R'
            flash('Categoria de Receita atualizada com sucesso!', 'success')
        db.session.commit()
    else:
        flash('Erro ao processar o formulário da Categoria de Receita. Verifique os dados.', 'danger')
    
    return redirect(url_for('financeiro.revenue_categories'))

@financeiro_bp.route('categorias-receita/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_revenue_category(category_id):
    """Exclui uma categoria de receita, mas apenas se não houver transações ligadas a ela."""
    category = db.get_or_404(RevenueCategory, category_id)

    if category.user_id != current_user.id:
        abort(403)
        
    # ATUALIZAÇÃO CRÍTICA: Checar RevenueTransaction
    if category.transactions.count() > 0:
        flash('Não é possivel excluir a categoria de Receita, pois há transações ligadas a ela.', 'danger')
        return redirect(url_for('financeiro.revenue_categories'))
    
    db.session.delete(category)
    db.session.commit()
    flash('Categoria de Receita excluída com sucesso!', 'info')

    return redirect(url_for('financeiro.revenue_categories'))
    
# ----------------------------------------------------------------------
# 3. Rotas de Configuração de Despesa (ExpenseGroup e ExpenseItem)
# ----------------------------------------------------------------------
@financeiro_bp.route('/configuracao-despesa')
@login_required
def expense_config():
    """Gerencia grupos e itens de despesa."""
    groups = ExpenseGroup.query.filter_by(user_id=current_user.id).order_by(ExpenseGroup.name).all()
    # Adicionando o join para ordenação mais lógica
    items = ExpenseItem.query.join(ExpenseGroup).filter(ExpenseItem.user_id == current_user.id).order_by(ExpenseGroup.name, ExpenseItem.name).all()

    form_group = ExpenseGroupForm()
    form_item = ExpenseItemForm()
    
    # O QuerySelectField é populado automaticamente pelo query_factory no forms.py
    
    return render_template('financeiro/expense_config.html', # Novo template
                           groups=groups,
                           items=items,
                           form_group=form_group,
                           form_item=form_item,
                           title='Configuração de Despesas',
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
        # Erro de validação: melhor prática seria retornar com o formulário, mas redirecionamos para simplicidade
        flash('Erro ao adicionar Grupo de Despesa. Verifique os dados.', 'danger')
    return redirect(url_for('financeiro.expense_config'))

@financeiro_bp.route('/configuracao-despesa/item/add', methods=['POST'])
@login_required
def add_expense_item():
    form = ExpenseItemForm()
    # Força a query para o QuerySelectField para garantir que a validação funcione
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
        flash('Erro ao adicionar Item de Despesa. Verifique os dados.', 'danger')
    return redirect(url_for('financeiro.expense_config'))

# Rotas de DELETE para a hierarquia de despesa (Simplificado)
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
    return redirect(url_for('financeiro.expense_config'))

@financeiro_bp.route('/configuracao-despesa/item/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_expense_item(item_id):
    item = db.get_or_404(ExpenseItem, item_id)
    if item.user_id != current_user.id:
        abort(403)
    # ATUALIZAÇÃO CRÍTICA: Checar Expense
    if item.expenses.count() > 0:
        flash('Não é possível excluir o item, pois há despesas ligadas a ele.', 'danger')
        return redirect(url_for('financeiro.expense_config'))
        
    db.session.delete(item)
    db.session.commit()
    flash('Item de Despesa excluído com sucesso!', 'info')
    return redirect(url_for('financeiro.expense_config'))


# ----------------------------------------------------------------------
# 4. Rotas de RECEITAS (RevenueTransaction) - SUBSTITUEM AS DE TRANSACTION
# ----------------------------------------------------------------------

# REDIRECIONAMENTOS (CRÍTICOS)
# As rotas antigas de /transacoes devem ser redirecionadas para as novas, evitando links quebrados.
@financeiro_bp.route('/transacoes')
@login_required
def transactions():
    # Rota antiga de listagem de transações deve ser redirecionada para Despesas
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
    """Lista todas as Receitas (RevenueTransaction) do usuário."""
    page = request.args.get('page', 1, type=int)
    per_page = 10

    pagination = RevenueTransaction.query.filter_by(user_id=current_user.id) \
                                         .order_by(RevenueTransaction.date.desc()) \
                                         .paginate(page=page, per_page=per_page, error_out=False)

    all_revenues = pagination.items

    total_revenue_amount = db.session.scalar(
        db.select(func.coalesce(func.sum(RevenueTransaction.amount), 0.00)).where(
            RevenueTransaction.user_id == current_user.id
        )
    )
    
    # Usa o formulário de Receita apenas para choices (se necessário)
    form = RevenueTransactionForm() 

    return render_template('financeiro/revenues.html', 
                           transactions=all_revenues,
                           pagination=pagination,
                           total_revenue_amount=total_revenue_amount,
                           title='Minhas Receitas', **footer)

@financeiro_bp.route('/receitas/add', methods=['GET', 'POST'])
@login_required
def add_revenue():
    """Rota para adicionar uma nova RECEITA."""
    form = RevenueTransactionForm() # Novo formulário
    
    if not current_user.wallets.first():
        flash('Você precisa adicionar pelo menos uma Carteira antes de registrar uma Receita!', 'warning')
        return redirect(url_for('financeiro.wallets'))
    if not current_user.categories.first(): # current_user.categories agora é RevenueCategory
        flash('Você precisa adicionar pelo menos uma Categoria de Receita antes de registrar uma Receita!', 'warning')
        return redirect(url_for('financeiro.revenue_categories'))
        
    if form.validate_on_submit():
        revenue = RevenueTransaction( # Novo Modelo
            description=form.description.data,
            amount=form.amount.data,
            date=form.date.data,
            type='R', # Força para Receita
            is_recurrent=False, # Não permite recorrência por aqui
            frequency=None,
            user_id=current_user.id,
            wallet_id=form.wallet.data.id,
            category_id=form.category.data.id
        )
        db.session.add(revenue)
        db.session.commit()
        
        flash('Receita registrada com sucesso!', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('financeiro/revenue_form.html', # Novo template
                           form=form, 
                           title='Nova Receita',
                           is_edit=False,
                           transaction_id=None, **footer)

@financeiro_bp.route('/receitas/edit/<int:revenue_id>', methods=['GET', 'POST'])
@login_required
def edit_revenue(revenue_id):
    """Rota para editar uma RECEITA existente."""
    
    revenue = db.get_or_404(RevenueTransaction, revenue_id) # Novo Modelo
    if revenue.user_id != current_user.id:
        abort(403)
        
    form = RevenueTransactionForm(obj=revenue) # Novo Formulário
    
    if request.method == 'GET':
        # Popula os campos customizados no GET
        form.description.data = revenue.description
        form.amount.data = revenue.amount
        form.date.data = revenue.date
        
        # NOTE: A QuerySelectField requer que o objeto seja setado, não apenas o ID.
        form.wallet.data = revenue.wallet
        form.category.data = revenue.category

    if form.validate_on_submit():
        revenue.description = form.description.data
        revenue.amount = form.amount.data
        revenue.date = form.date.data
        # Type e recorrência são ignorados/mantidos 'R'/False
            
        revenue.wallet_id = form.wallet.data.id
        revenue.category_id = form.category.data.id
        
        db.session.commit()
        flash('Receita atualizada com sucesso!', 'success')
        return redirect(url_for('financeiro.revenues'))
        
    
    return render_template('financeiro/revenue_form.html', # Novo template
                           form=form, 
                           title='Editar Receita',
                           is_edit=True,
                           transaction_id=revenue_id, **footer)

@financeiro_bp.route('/receitas/delete/<int:revenue_id>', methods=['POST'])
@login_required
def delete_revenue(revenue_id):
    """Rota para excluir uma RECEITA."""
    revenue = db.get_or_404(RevenueTransaction, revenue_id) # Novo Modelo
    
    if revenue.user_id != current_user.id:
        abort(403)
        
    try:
        db.session.delete(revenue)
        db.session.commit()
        flash('Receita excluída com sucesso!', 'info')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir a Receita: {e}', 'danger')
        
    return redirect(url_for('financeiro.revenues'))

# ----------------------------------------------------------------------
# 5. Rotas de DESPESAS (Expense)
# ----------------------------------------------------------------------
@financeiro_bp.route('/despesas')
@login_required
def expenses():
    """Lista todas as Despesas (pagas e pendentes) do usuário."""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    now_date = date.today()
    
    # Base query (não filtrada por status ainda)
    base_query = Expense.query.filter_by(user_id=current_user.id) 

    # --- NOVO: CÁLCULO DE TOTAIS NÃO PAGINADOS (Backend) ---
    
    # Total Pago (Todos os registros, independente da página)
    total_paid_query = db.session.scalar(
        db.select(func.coalesce(func.sum(Expense.amount), Decimal(0))).where(
            Expense.user_id == current_user.id,
            Expense.is_paid == True
        )
    )
    total_paid_amount = total_paid_query if total_paid_query is not None else Decimal(0)
    
    # Total Pendente (Todos os registros, independente da página)
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
                           **footer)

@financeiro_bp.route('/despesas/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    """Rota para adicionar uma nova DESPESA."""
    form = ExpenseForm() # Novo formulário
    
    if not current_user.wallets.first():
        flash('Você precisa adicionar pelo menos uma Carteira antes de registrar uma Despesa!', 'warning')
        return redirect(url_for('financeiro.wallets'))
    if not current_user.expense_items.first():
        flash('Você precisa configurar Itens de Despesa antes de registrar uma Despesa!', 'warning')
        return redirect(url_for('financeiro.expense_config'))
        
    if form.validate_on_submit():
        is_paid = (form.status.data == 'paid')
        
        expense = Expense( # Novo Modelo
            description=form.description.data,
            amount=form.amount.data,
            date=form.date.data,
            due_date=form.due_date.data,
            is_paid=is_paid,
            payment_date=datetime.combine(form.payment_date.data, datetime.min.time()) if is_paid and form.payment_date.data else None,
            
            is_recurrent=form.is_recurrent.data,
            frequency=form.frequency.data if form.is_recurrent.data else None,
            
            user_id=current_user.id,
            wallet_id=form.wallet.data.id,
            item_id=form.item.data.id # Novo relacionamento
        )
        
        db.session.add(expense)
        db.session.commit()
        
        msg = 'Despesa registrada como PAGA com sucesso!' if is_paid else 'Despesa registrada como PENDENTE com sucesso!'
        flash(msg, 'success')
        return redirect(url_for('financeiro.expenses'))
    
    # Popula o formulário para GET/erros (opcional, mas bom para UX)
    if request.method == 'GET' and not form.status.data:
        form.status.data = 'pending' # Default para pendente

    return render_template('financeiro/expense_form.html', # Novo template
                           form=form, 
                           title='Novo Lançamento de Despesa',
                           is_edit=False,
                           expense_id=None, **footer)

@financeiro_bp.route('/despesas/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    """Rota para editar uma DESPESA existente."""
    
    expense = db.get_or_404(Expense, expense_id) # Novo Modelo
    if expense.user_id != current_user.id:
        abort(403)
        
    # obj=expense popula os campos do modelo (description, amount, date, due_date...)
    form = ExpenseForm(obj=expense) # Novo Formulário
    
    if request.method == 'GET':
        form.status.data = 'paid' if expense.is_paid else 'pending'
        form.payment_date.data = expense.payment_date.date() if expense.payment_date else None
        
        # Popula QuerySelectFields
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
        
    
    return render_template('financeiro/expense_form.html', # Novo template
                           form=form, 
                           title='Editar Despesa',
                           is_edit=True,
                           expense_id=expense_id, **footer)

@financeiro_bp.route('/despesas/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """Rota para excluir uma DESPESA."""
    expense = db.get_or_404(Expense, expense_id) # Novo Modelo
    
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
    """Rota para dar baixa em uma DESPESA PENDENTE."""
    expense = db.get_or_404(Expense, expense_id)
    
    if expense.user_id != current_user.id:
        abort(403)

    if expense.is_paid:
        flash('Esta despesa já está marcada como paga.', 'warning')
        return redirect(url_for('financeiro.expenses'))
        
    expense.is_paid = True
    expense.payment_date = datetime.utcnow() # Marca com a data atual UTC
    
    try:
        db.session.commit()
        flash(f'Despesa "{expense.description}" paga com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao dar baixa na despesa: {e}', 'danger')

    return redirect(url_for('financeiro.expenses'))
