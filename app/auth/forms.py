from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, RadioField
from flask_login import current_user
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from .models import User

class LoginForm(FlaskForm):
    """Formulário para a tela de Login."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

class RegistrationForm(FlaskForm):
    """Formulário para a tela de Cadastro de Novo Usuário."""
    username = StringField('Nome de Usuário', validators=[
        DataRequired(), Length(min=3, max=64, message="O nome deve ter entre 3 e 64 caracteres.")
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[
        DataRequired(), Length(min=6, message="A senha deve ter no mínimo 6 caracteres.")
    ])
    password2 = PasswordField(
        'Repetir Senha', validators=[DataRequired(), EqualTo(
            'password', message='As senhas devem ser iguais.'
        )])
    submit = SubmitField('Registrar')
    
    def validate_username(self, username):
        """Verifica se o nome de usuário já existe no banco."""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Este nome de usuário já está em uso.')
    
    def validate_email(self, email):
        """Verifica se o email já está registrado."""
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Este email já está registrado.')

class ChangePasswordForm(FlaskForm):
    """Formulário para mudança de senha."""
    old_password = PasswordField('Senha Atual', validators=[DataRequired()])
    password = PasswordField('Nova Senha', validators=[
        DataRequired(), Length(min=6, message="A senha deve ter no mínimo 6 caracteres.")
    ])
    password2 = PasswordField(
        'Repetir Nova Senha', validators=[DataRequired(), EqualTo(
            'password', message='As senhas devem ser iguais.'
        )])
    submit = SubmitField('Alterar Senha')
    
    def validate_old_password(self, old_password):
        if not current_user.check_password(old_password.data):
            raise ValidationError('A senha atual está incorreta.')


class ChangeEmailForm(FlaskForm):
    email = StringField('Novo Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Alterar Email')

    def validate_email(self, email):
        if email.data != current_user.email:
            from .models import User 
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Este email já está registrado por outra conta.')

class ResetDataForm(FlaskForm):
    action_type = RadioField('Selecione a Ação:', choices=[
        ('transactions', 'Limpar Lançamentos (Manter categorias e carteiras)'),
        ('full_reset', 'Reset Completo (Apagar tudo e zerar conta)'),
        ('delete_account', 'Excluir Minha Conta (Apagar usuário e dados)')
    ], default='transactions', validators=[DataRequired()])
    
    password = PasswordField('Senha para Confirmação', validators=[DataRequired()])
    confirm_check = BooleanField('Estou ciente que esta ação é irreversível', validators=[DataRequired()])
    submit = SubmitField('CONFIRMAR AÇÃO')
