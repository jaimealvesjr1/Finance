from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, DateField, SubmitField, TextAreaField, PasswordField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo
from app.auth.models import User
from wtforms import ValidationError
from datetime import date

class AdminUserForm(FlaskForm):
    """Formulário para edição de usuários por um Admin."""
    username = StringField('Nome de Usuário', validators=[
        DataRequired(), 
        Length(min=3, max=64)
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    
    is_admin = BooleanField('Permissão de Administrador')
    
    access_due_date = DateField(
        'Vencimento do Acesso (Mensalidade)', 
        format='%Y-%m-%d', 
        validators=[Optional()]
    )

    pending_message = TextAreaField(
        'Mensagem para o Usuário (Próximo Acesso)',
        validators=[Optional(), Length(max=500)]
    )
    
    submit = SubmitField('Salvar Alterações')
    
    def validate_unique_email(self, field, user_id):
        user = User.query.filter(User.email == field.data).first()
        if user is not None and user.id != user_id:
            raise ValidationError('Este email já está registrado por outra conta.')

    def validate_unique_username(self, field, user_id):
        user = User.query.filter(User.username == field.data).first()
        if user is not None and user.id != user_id:
            raise ValidationError('Este nome de usuário já está em uso por outra conta.')

class AdminChangePasswordForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[
        DataRequired(message="A nova senha é obrigatória."), 
        Length(min=6, message="A senha deve ter no mínimo 6 caracteres.")
    ])
    password2 = PasswordField(
        'Repetir Nova Senha', 
        validators=[
            DataRequired(message="A confirmação da senha é obrigatória."), 
            EqualTo('password', message='As senhas devem ser iguais.')
        ]
    )
    submit = SubmitField('Redefinir Senha')

class AdminBroadcastForm(FlaskForm):
    broadcast_message = TextAreaField(
        'Conteúdo da Mensagem para TODOS',
        validators=[DataRequired(message="A mensagem não pode ser vazia."), Length(max=500)]
    )
    submit = SubmitField('Enviar Mensagem para Todos')