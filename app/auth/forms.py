from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from .models import User

class LoginForm(FlaskForm):
    """Formulário para a tela de Login."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
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
