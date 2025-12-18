from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.auth.models import User
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, ChangeEmailForm, ResetDataForm
from app.financeiro.models import Wallet, RevenueCategory, ExpenseCategory, RevenueTransaction, Expense, Transfer
from .models import User
from config import Config
from datetime import date, timedelta

auth_bp = Blueprint('auth', __name__, template_folder='templates')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}

def flash_form_errors(form):
    """Função de utilidade para exibir erros do formulário."""
    for field_name, errors in form.errors.items():
        for error in errors:
            field_obj = getattr(form, field_name, None)
            field_label = field_obj.label.text if field_obj and hasattr(field_obj, 'label') else field_name
            flash(f"Erro no campo '{field_label}': {error}", 'danger')

@auth_bp.route('/perfil', methods=['GET'])
@login_required
def profile():
    form_password = ChangePasswordForm()
    form_email = ChangeEmailForm(obj=current_user) 
    form_reset = ResetDataForm()
    
    return render_template('auth/profile.html', 
                           form_password=form_password,
                           form_email=form_email,
                           form_reset=form_reset,
                           title='Meu Perfil',
                           **footer)

@auth_bp.route('/perfil/reset_data', methods=['POST'])
@login_required
def reset_account_data():
    form = ResetDataForm()
    
    # Validação do formulário
    if form.validate_on_submit():
        # 1. Checagem de segurança (Senha)
        if not current_user.check_password(form.password.data):
            flash('Senha incorreta. Nenhuma alteração foi feita.', 'danger')
            return redirect(url_for('auth.profile'))
            
        action = form.action_type.data
        
        try:
            # BLOCO A: Apagar Lançamentos (Comum a todas as opções)
            # Removemos transações financeiras primeiro
            RevenueTransaction.query.filter_by(user_id=current_user.id).delete()
            Expense.query.filter_by(user_id=current_user.id).delete()
            Transfer.query.filter_by(user_id=current_user.id).delete()
            
            msg = 'Todos os lançamentos foram apagados com sucesso.'
            
            # BLOCO B: Reset Completo ou Exclusão (Apagar Estrutura)
            if action in ['full_reset', 'delete_account']:
                RevenueCategory.query.filter_by(user_id=current_user.id).delete()
                ExpenseCategory.query.filter_by(user_id=current_user.id).delete()
                Wallet.query.filter_by(user_id=current_user.id).delete()
                msg = 'Sua conta foi totalmente resetada para o estado inicial.'
            
            # BLOCO C: Exclusão da Conta (Apagar Usuário)
            if action == 'delete_account':
                user_to_delete = User.query.get(current_user.id)
                
                if user_to_delete:
                    db.session.delete(user_to_delete)
                    db.session.commit()
                    
                    logout_user()
                    
                    flash('Sua conta e todos os seus dados foram excluídos permanentemente. Até logo.', 'info')
                    return redirect(url_for('auth.login'))
                
            db.session.commit()
            flash(msg, 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro crítico ao processar solicitação: {e}', 'danger')
            
    else:
        flash('Por favor, confirme que está ciente e preencha a senha.', 'warning')
            
    return redirect(url_for('auth.profile'))

@auth_bp.route('/perfil/change_password', methods=['POST'])
@login_required
def change_password():
    form_password = ChangePasswordForm()
    if form_password.validate_on_submit():
        current_user.set_password(form_password.password.data)
        db.session.commit()
        flash('Sua senha foi alterada com sucesso!', 'success')
        return redirect(url_for('auth.profile'))
    
    # Se a validação falhar, repasse os forms com erros
    form_email = ChangeEmailForm(obj=current_user)
    flash_form_errors(form_password)
    
    return render_template('auth/profile.html', 
                           form_password=form_password,
                           form_email=form_email,
                           title='Meu Perfil',
                           **footer)

@auth_bp.route('/perfil/change_email', methods=['POST'])
@login_required
def change_email():
    form_email = ChangeEmailForm()
    if form_email.validate_on_submit():
        current_user.email = form_email.email.data
        db.session.commit()
        # Necessário re-logar o usuário com o novo email, se o Flask-Login
        # usar o email para identificação (embora a implementação atual use ID).
        # Manter o login atual é seguro, mas um flush de logout/login é mais robusto.
        
        # Neste caso, vamos apenas atualizar e redirecionar
        flash('Seu email foi alterado com sucesso!', 'success')
        return redirect(url_for('auth.profile'))
    
    # Se a validação falhar, repasse os forms com erros
    form_password = ChangePasswordForm()
    flash_form_errors(form_email)
    
    return render_template('auth/profile.html', 
                           form_password=form_password,
                           form_email=form_email,
                           title='Meu Perfil',
                           **footer)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Email ou senha inválidos. Tente novamente.', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_functional_active:
            due_date_str = user.access_due_date.strftime("%d/%m/%Y") if user.access_due_date else 'DATA INDEFINIDA'
            flash(f'Seu acesso está suspenso desde {due_date_str}. Renove sua assinatura para acessar.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)
        flash(f'Bem-vindo(a) de volta, {user.username}!', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('auth/login.html', form=form, title='Login', **footer)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.access_due_date = date.today() + timedelta(days=30)
        db.session.add(user)
        db.session.commit()

        flash('Seu cadastro foi realizado com sucesso! Faça login para continuar.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form, title='Registro', **footer)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você desconectou sua conta.', 'info')
    return redirect(url_for('auth.login'))
 
@auth_bp.route('/alerta-critico')
def critical_alert():
    if 'CRITICAL_MESSAGE' not in session:
        return redirect(url_for('main.index'))
        
    context = session.pop('CRITICAL_MESSAGE') 
    
    return render_template('auth/critical_alert.html', context=context)
