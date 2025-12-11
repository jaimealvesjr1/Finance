from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.auth.models import User
from sqlalchemy import update
from config import Config
from datetime import datetime
from .forms import AdminUserForm, AdminChangePasswordForm, AdminBroadcastForm
import functools

admin_bp = Blueprint('admin', __name__, template_folder='templates', url_prefix='/admin')
footer = {'ano': Config.ANO_ATUAL, 'versao': Config.VERSAO_APP}

def flash_form_errors(form):
    """Função de utilidade para exibir erros do formulário."""
    for field_name, errors in form.errors.items():
        for error in errors:
            field_obj = getattr(form, field_name, None)
            field_label = field_obj.label.text if field_obj and hasattr(field_obj, 'label') else field_name
            flash(f"Erro no campo '{field_label}': {error}", 'danger')

def admin_required(f):
    """Decorator para garantir que apenas admins acessem a rota."""
    @functools.wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Acesso negado: Você não tem permissão de administrador.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def list_users():
    users = User.query.all()
    edit_forms = {}
    reset_password_forms = {}
    broadcast_form = AdminBroadcastForm()

    for user in users:
        form = AdminUserForm(obj=user)
        if user.access_due_date:
            form.access_due_date.data = user.access_due_date
        edit_forms[user.id] = form
        
        reset_password_forms[user.id] = AdminChangePasswordForm()
    
    return render_template('admin/list_users.html',
                           users=users,
                           edit_forms=edit_forms,
                           reset_password_forms=reset_password_forms,
                           broadcast_form=broadcast_form,
                           title='Gestão de Usuários (Admin)',
                           **footer)

@admin_bp.route('/broadcast', methods=['POST'])
@admin_required
def broadcast_message():
    form = AdminBroadcastForm() 
    
    if form.validate_on_submit():
        try:
            message_content = form.broadcast_message.data
            
            db.session.execute(
                update(User)
                .where(User.id != current_user.id)
                .values(pending_message=message_content)
            )
            
            if current_user.pending_message:
                 current_user.pending_message = None
            
            db.session.commit()
            
            flash(f'Mensagem de broadcast enviada com sucesso para todos os usuários. Será exibida na próxima visita.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao enviar a mensagem para todos os usuários: {e}', 'danger')
            
    else:
        flash_form_errors(form)
        
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/usuarios/edit/<int:user_id>', methods=['POST'])
@admin_required
def edit_user(user_id):
    user = db.get_or_404(User, user_id)
    form = AdminUserForm() 
    
    form.validate_email = lambda f: form.validate_unique_email(f, user_id=user.id)
    form.validate_username = lambda f: form.validate_unique_username(f, user_id=user.id)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        
        user.access_due_date = form.access_due_date.data
        
        user.pending_message = form.pending_message.data
        if not user.pending_message or user.pending_message.strip() == '':
             user.pending_message = None

        db.session.commit()
        flash(f'Usuário "{user.username}" atualizado com sucesso!', 'success')
    else:
        flash_form_errors(form)
        flash('Erro ao editar usuário. Verifique os dados.', 'danger')
        
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/usuarios/reset_password/<int:user_id>', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    user = db.get_or_404(User, user_id)
    form = AdminChangePasswordForm() 

    if form.validate_on_submit():
        try:
            user.set_password(form.password.data)
            db.session.commit()
            flash(f'Senha do usuário "{user.username}" redefinida com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao redefinir a senha: {e}', 'danger')
    else:
        flash_form_errors(form)
        flash('Erro na redefinição de senha. Verifique se as senhas coincidem e atendem ao requisito de tamanho.', 'danger')
        
    return redirect(url_for('admin.list_users'))
