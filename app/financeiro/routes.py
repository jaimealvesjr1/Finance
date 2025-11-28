from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.exceptions import abort
from flask_login import login_required, current_user
from app.extensions import db
from .models import Wallet, Category, Transaction
from .forms import WalletForm, CategoryForm, TransactionForm
from config import Config

financeiro_bp = Blueprint('financeiro', __name__, template_folder='templates', url_prefix='/financeiro')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}

# ----------------------------------------------------------------------
# 1. Rotas de Carteiras (Wallets)
# ----------------------------------------------------------------------
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
            wallet.name = form.name.data
            wallet.initial_balance.data
            flash('Carteira atualizada com sucesso!', 'success')
        db.session.commit()
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Erro no formulário da Carteira {error}', 'danger')
    return redirect(url_for('financeiro.wallets'))

@financeiro_bp.route('carteiras/delete/<int:wallet_id>', methods=['POST'])
@login_required
def delete_wallet(wallet_id):
    """Exclui uma carteira, mas apenas se não houver transações ligadas a ela."""
    wallet = db.get_or_404(Wallet, wallet_id)
    
    if wallet.user_id != current_user.id:
        abort(403)
    if wallet.transactions.count() > 0:
        flash('Não é possível excluir a carteira, pois há transações ligadas a ela.', 'danger')
        return redirect(url_for('financeiro.wallets'))
    
    db.session.delete(wallet)
    db.session.commit()
    flash('Carteira excluída com sucesso!', 'info')

    return redirect(url_for('financeiro.wallets'))

# ----------------------------------------------------------------------
# 2. Rotas de Categorias (Categories)
# ----------------------------------------------------------------------
@financeiro_bp.route('/categorias')
@login_required
def categories():
    """Lista todas as categorias do usuário e permite adicionar uma nova."""
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.type, Category.name).all()
    form = CategoryForm()
    return render_template('financeiro/categories.html', categories=categories, form=form, title='Minhas Categorias', **footer)

@financeiro_bp.route('/categorias/add', methods=['POST'])
@login_required
def add_category():
    """Processa a adição de uma nova categoria."""
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            type=form.type.data,
            user_id=current_user.id
        )
        db.session.add(category)
        db.session.commit()
        flash('Categoria adicionada com sucesso!', 'success')
    else:
        flash('Erro ao adicionar categoria. Verifique os dados.', 'danger')
    
    return redirect(url_for('financeiro.categories'))

@financeiro_bp.route('/categorias/manage', defaults={'category_id': None}, methods=['POST'])
@financeiro_bp.route('/categorias/manage/<int:category_id>', methods=['POST'])
@login_required
def manage_category(category_id):
    """Processa a adição (sem ID) ou edição (com ID) de uma categoria."""
    form = CategoryForm()

    if form.validate_on_submit():
        if category_id is None:
            category = Category(
                name=form.name.data,
                type=form.type.data,
                user_id=current_user.id)
            db.session.add(category)
            flash('Categoria adicionada com sucesso!', 'success')
        else:
            category = db.get_or_404(Category, category_id)
            if category.user_id != current_user.id:
                abort(403)
            category.name = form.name.data
            category.type = form.type.data
            flash('Categoria atualizada com sucesso!', 'success')
        db.session.commit()
    else:
        flash('Erro ao processar o formulário da Categoria. Verifique os dados.', 'danger')
    
    return redirect(url_for('financeiro.categories'))

@financeiro_bp.route('categorias/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    """Exclui uma categoria, mas apenas se não houver transações ligadas a ela."""
    category = db.get_or_404(Category, category_id)

    if category.user_id != current_user.id:
        abort(403)
    if category.transactions.count() > 0:
        flash('Não é possivel excluir a carteira, pois há transações ligadas a ela.', 'danger')
        return redirect(url_for('financeiro.categories'))
    
    db.session.delete(category)
    db.session.commit()
    flash('Categoria excluída com sucesso!', 'info')

    return redirect(url_for('financeiro.categories'))

# ----------------------------------------------------------------------
# 3. Rotas de Transações (Transactions)
# ----------------------------------------------------------------------
@financeiro_bp.route('/transacoes/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    """Rota para adicionar uma nova transação."""
    form = TransactionForm()
    
    if not current_user.wallets.first():
        flash('Você precisa adicionar pelo menos uma Carteira antes de registrar uma Transação!', 'warning')
        return redirect(url_for('financeiro.wallets'))
    if not current_user.categories.first():
        flash('Você precisa adicionar pelo menos uma Categoria antes de registrar uma Transação!', 'warning')
        return redirect(url_for('financeiro.categories'))
        
    if form.validate_on_submit():
        transaction = Transaction(
            description=form.description.data,
            amount=form.amount.data,
            date=form.date.data,
            type=form.type.data,
            is_recurrent=form.is_recurrent.data,
            frequency=form.frequency.data if form.is_recurrent.data else None,
            user_id=current_user.id,
            wallet_id=form.wallet.data.id,
            category_id=form.category.data.id
        )
        db.session.add(transaction)
        db.session.commit()
        
        flash('Transação registrada com sucesso!', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('financeiro/transaction_form.html', 
                           form=form, 
                           title='Nova Transação',
                           is_edit=False,
                           transaction_id=None, **footer)

@financeiro_bp.route('/transacoes/edit/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    """Rota para editar uma transação existente."""
    
    transaction = db.get_or_404(Transaction, transaction_id)
    if transaction.user_id != current_user.id:
        abort(403)
        
    form = TransactionForm()
    
    if form.validate_on_submit():
        transaction.description = form.description.data
        transaction.amount = form.amount.data
        transaction.date = form.date.data
        transaction.type = form.type.data
        transaction.is_recurrent = form.is_recurrent.data
        
        if form.is_recurrent.data:
            transaction.frequency = form.frequency.data
        else:
            transaction.frequency = None
            
        transaction.wallet_id = form.wallet.data.id
        transaction.category_id = form.category.data.id
        
        db.session.commit()
        flash('Transação atualizada com sucesso!', 'success')
        return redirect(url_for('financeiro.transactions'))
        
    elif request.method == 'GET':
        form.description.data = transaction.description
        form.amount.data = transaction.amount
        form.date.data = transaction.date
        form.type.data = transaction.type
        form.is_recurrent.data = transaction.is_recurrent
        form.frequency.data = transaction.frequency
        
        form.wallet.data = transaction.wallet
        form.category.data = transaction.category
    
    return render_template('financeiro/transaction_form.html', 
                           form=form, 
                           title='Editar Transação',
                           is_edit=True,
                           transaction_id=transaction_id, **footer)

@financeiro_bp.route('/transacoes/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    """Rota para excluir uma transação."""
    transaction = db.get_or_404(Transaction, transaction_id)
    
    if transaction.user_id != current_user.id:
        abort(403)
        
    try:
        db.session.delete(transaction)
        db.session.commit()
        flash('Transação excluída com sucesso!', 'info')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir a transação: {e}', 'danger')
        
    return redirect(url_for('financeiro.transactions'))

@financeiro_bp.route('/transacoes')
@login_required
def transactions():
    """Lista todas as transações do usuário, ordenadas por data."""
    all_transactions = Transaction.query.filter_by(user_id=current_user.id) \
                                        .filter_by(is_recurrent=False) \
                                        .order_by(Transaction.date.desc()) \
                                        .all()

    form = TransactionForm()
    frequency_choices = {key: label for key, label in form.frequency.choices if key}    

    return render_template('financeiro/transactions.html',
                           transactions=all_transactions,
                           frequency_choices=frequency_choices,
                           title='Todas as Movimentações', **footer)
