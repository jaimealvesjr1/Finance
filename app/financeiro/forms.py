from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SubmitField, SelectField, BooleanField, DateField
from wtforms.validators import DataRequired, NumberRange, Length
from wtforms_sqlalchemy.fields import QuerySelectField
from datetime import date
from flask_login import current_user

from .models import Wallet, Category
from app.extensions import db

def get_user_wallets():
    """Retorna as carteiras/contas do usuário atual."""
    return Wallet.query.filter_by(user_id=current_user.id).all()

def get_user_categories():
    """Retorna as categorias do usuário atual."""
    return Category.query.filter_by(user_id=current_user.id).all()

# --- 1. Formulário de Carteira (Wallet) ---
class WalletForm(FlaskForm):
    name = StringField('Nome da Carteira/Conta', validators=[
        DataRequired(), 
        Length(max=80)
    ])
    initial_balance = DecimalField('Saldo Inicial (R$)', default=0.00, validators=[
        DataRequired(), 
        NumberRange(min=-10000000, message="Valor fora do limite.")
    ])
    submit = SubmitField('Salvar Carteira')

# --- 2. Formulário de Categoria (Category) ---
class CategoryForm(FlaskForm):
    name = StringField('Nome da Categoria', validators=[
        DataRequired(), 
        Length(max=80)
    ])
    type = SelectField('Tipo', choices=[
        ('R', 'Receita (Entrada)'), 
        ('D', 'Despesa (Saída)')
    ], validators=[DataRequired()])
    
    submit = SubmitField('Salvar Categoria')

# --- 3. Formulário de Transação (Transaction) ---
class TransactionForm(FlaskForm):
    description = StringField('Descrição', validators=[
        DataRequired(), 
        Length(max=255)
    ])
    amount = DecimalField('Valor (R$)', validators=[
        DataRequired(), 
        NumberRange(min=0.01, message="O valor deve ser positivo.")
    ])
    date = DateField('Data', default=date.today, format='%Y-%m-%d', validators=[DataRequired()])
    
    type = SelectField('Tipo de Movimento', choices=[
        ('R', 'Receita'), 
        ('D', 'Despesa')
    ], validators=[DataRequired()])
    
    wallet = QuerySelectField(
        'Carteira/Conta',
        query_factory=get_user_wallets,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
        validators=[DataRequired(message="Selecione uma carteira.")]
    )
    
    category = QuerySelectField(
        'Categoria',
        query_factory=get_user_categories,
        get_pk=lambda a: a.id,
        get_label=lambda a: f"{a.name} ({a.type})",
        allow_blank=False,
        validators=[DataRequired(message="Selecione uma categoria.")]
    )

    is_recurrent = BooleanField('Marcar como Transação Recorrente (Ex: Assinatura, Salário Fixo)')
    frequency = SelectField('Frequência de Recorrência', choices=[
        ('', 'Não Recorrente'),
        ('daily', 'Diária'), 
        ('weekly', 'Semanal'), 
        ('monthly', 'Mensal'), 
        ('yearly', 'Anual')
    ], default='')
    
    submit = SubmitField('Registrar Transação')
