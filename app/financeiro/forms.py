from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SubmitField, SelectField, BooleanField, DateField
from wtforms.validators import DataRequired, NumberRange, Length, ValidationError, Optional
from wtforms_sqlalchemy.fields import QuerySelectField
from datetime import date
from flask_login import current_user

from .models import Wallet, RevenueCategory, RevenueTransaction, ExpenseGroup, ExpenseItem, Expense 
from app.extensions import db

def get_user_wallets():
    return Wallet.query.filter_by(user_id=current_user.id).all()

def get_user_revenue_categories():
    return RevenueCategory.query.filter_by(user_id=current_user.id).all()

def get_user_expense_items():
    return ExpenseItem.query.join(ExpenseGroup).filter(ExpenseItem.user_id == current_user.id).order_by(ExpenseGroup.name, ExpenseItem.name).all()

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

class RevenueCategoryForm(FlaskForm):
    name = StringField('Nome da Categoria de Receita', validators=[
        DataRequired(), 
        Length(max=80)
    ])
    submit = SubmitField('Salvar Categoria de Receita')

class ExpenseGroupForm(FlaskForm):
    name = StringField('Nome do Grupo de Despesa (Ex: Moradia, Lazer)', validators=[
        DataRequired(), 
        Length(max=80)
    ])
    submit = SubmitField('Salvar Grupo de Despesa')

class ExpenseItemForm(FlaskForm):
    name = StringField('Nome do Item de Despesa (Ex: Aluguel, Supermercado)', validators=[
        DataRequired(), 
        Length(max=150)
    ])
    group = QuerySelectField(
        'Grupo de Despesa',
        query_factory=lambda: ExpenseGroup.query.filter_by(user_id=current_user.id).order_by(ExpenseGroup.name).all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
        validators=[DataRequired(message="Selecione um grupo de despesa.")]
    )
    submit = SubmitField('Salvar Item de Despesa')


class RevenueTransactionForm(FlaskForm):
    description = StringField('Descrição da Receita', validators=[
        DataRequired(), 
        Length(max=255)
    ])
    amount = DecimalField('Valor (R$)', validators=[
        DataRequired(), 
        NumberRange(min=0.01, message="O valor deve ser positivo.")
    ])
    
    due_date = DateField('Data de Vencimento', default=date.today, format='%Y-%m-%d', validators=[DataRequired()])
    date = DateField('Data de Competência/Registro', default=date.today, format='%Y-%m-%d', validators=[DataRequired()])
    
    status = SelectField('Situação', choices=[
        ('pending', 'A Receber (Agendado)'), 
        ('received', 'Recebido (Realizado)')
    ], validators=[DataRequired()])
    
    receipt_date = DateField('Data de Recebimento (Opcional)', format='%Y-%m-%d', validators=[Optional()])

    wallet = QuerySelectField(
        'Carteira/Conta',
        query_factory=get_user_wallets,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
        validators=[DataRequired(message="Selecione uma carteira.")]
    )
    
    category = QuerySelectField(
        'Categoria de Receita',
        query_factory=get_user_revenue_categories, 
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
        validators=[DataRequired(message="Selecione uma categoria de receita.")]
    )

    is_recurrent = BooleanField('Transação Recorrente?')
    frequency = SelectField('Frequência de Recorrência', choices=[
        ('', 'Não Recorrente'),
        ('daily', 'Diária'), 
        ('weekly', 'Semanal'), 
        ('monthly', 'Mensal'), 
        ('yearly', 'Anual')
    ], default='', validators=[Optional()])

    submit = SubmitField('Registrar Receita')
    
    def validate_receipt_date(self, field):
        if self.status.data == 'received':
            if not field.data:
                 raise ValidationError('A data de recebimento é obrigatória para receitas recebidas.')
            if field.data > date.today():
                 raise ValidationError('A data de recebimento não pode ser futura.')
    
    def validate_due_date(self, field):
        if field.data < self.date.data:
            raise ValidationError('A data de vencimento não pode ser anterior à data de registro.')
    
class ExpenseForm(FlaskForm):
    description = StringField('Descrição da Despesa', validators=[
        DataRequired(), 
        Length(max=255)
    ])
    amount = DecimalField('Valor (R$)', validators=[
        DataRequired(), 
        NumberRange(min=0.01, message="O valor deve ser positivo.")
    ])
    
    due_date = DateField('Data de Vencimento', default=date.today, format='%Y-%m-%d', validators=[DataRequired()])
    date = DateField('Data de Competência/Registro', default=date.today, format='%Y-%m-%d', validators=[DataRequired()])

    status = SelectField('Situação', choices=[
        ('pending', 'A Pagar (Agendado)'), 
        ('paid', 'Pago (Realizado)')
    ], validators=[DataRequired()])
    
    payment_date = DateField('Data de Pagamento (Opcional)', format='%Y-%m-%d', validators=[Optional()])

    item = QuerySelectField(
        'Item de Despesa',
        query_factory=get_user_expense_items,
        get_pk=lambda a: a.id,
        get_label=lambda a: f"{a.group.name} > {a.name}",
        allow_blank=False,
        validators=[DataRequired(message="Selecione um item de despesa.")]
    )
    
    wallet = QuerySelectField(
        'Carteira/Conta de Pagamento',
        query_factory=get_user_wallets,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
        validators=[DataRequired(message="Selecione uma carteira.")]
    )

    is_recurrent = BooleanField('Despesa Recorrente?')
    frequency = SelectField('Frequência de Recorrência', choices=[
        ('', 'Não Recorrente'),
        ('daily', 'Diária'), 
        ('weekly', 'Semanal'), 
        ('monthly', 'Mensal'), 
        ('yearly', 'Anual')
    ], default='', validators=[Optional()])

    submit = SubmitField('Registrar Despesa')
    
    def validate_payment_date(self, field):
        if self.status.data == 'paid':
            if not field.data:
                 raise ValidationError('A data de pagamento é obrigatória para despesas pagas.')
            if field.data > date.today():
                 raise ValidationError('A data de pagamento não pode ser futura.')
    
    def validate_due_date(self, field):
        if field.data < self.date.data:
            raise ValidationError('A data de vencimento não pode ser anterior à data de registro.')
