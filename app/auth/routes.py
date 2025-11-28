from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from .forms import LoginForm, RegistrationForm
from .models import User
from config import Config

auth_bp = Blueprint('auth', __name__, template_folder='templates')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}

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
 