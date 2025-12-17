from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SubmitField, SelectField, BooleanField, DateField
from wtforms.validators import DataRequired, NumberRange, Length, ValidationError, Optional
from wtforms_sqlalchemy.fields import QuerySelectField
from datetime import date
from flask_login import current_user

from .models import Wallet, RevenueCategory, RevenueTransaction, ExpenseCategory, Expense, Transfer 
from app.extensions import db

def get_user_wallets():
    return Wallet.query.filter_by(user_id=current_user.id).all()

def get_user_revenue_categories():
    return RevenueCategory.query.filter_by(user_id=current_user.id).all()

def get_user_expense_categories():
    return ExpenseCategory.query.filter(ExpenseCategory.user_id == current_user.id).order_by(ExpenseCategory.name).all()

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

class ExpenseCategoryForm(FlaskForm):
    name = StringField('Nome da Categoria de Despesa', validators=[
        DataRequired(), 
        Length(max=150)
    ])
    submit = SubmitField('Salvar Categoria de Despesa')


class RevenueTransactionForm(FlaskForm):
    description = StringField('Descrição', validators=[
        DataRequired(), 
        Length(max=255)
    ])
    amount = DecimalField('Valor (R$)', validators=[
        DataRequired(), 
        NumberRange(min=0.01, message="O valor deve ser positivo.")
    ])
    
    due_date = DateField('Data de Vencimento', default=date.today, format='%Y-%m-%d', validators=[DataRequired()])
    date = DateField('Data de Lançamento', default=date.today, format='%Y-%m-%d', validators=[DataRequired()])
    
    status = SelectField('Situação', choices=[
        ('pending', 'A Receber'), 
        ('received', 'Recebido')
    ], validators=[DataRequired()])
    
    receipt_date = DateField('Data de Recebimento', format='%Y-%m-%d', validators=[Optional()])

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

    is_recurrent = BooleanField('Transação se repete?')
    num_repetitions = SelectField('Repetir quantas vezes?', choices=[
        ('0', 'Apenas este lançamento'),
        ('1', '1 vez'),
        ('2', '2 vezes'), 
        ('3', '3 vezes'), 
        ('4', '4 vezes'), 
        ('5', '5 vezes'),
        ('6', '6 vezes'),
        ('7', '7 vezes'),
        ('8', '8 vezes'),
        ('9', '9 vezes'),
        ('10', '10 vezes'),
        ('11', '11 vezes')
    ], default='0', validators=[Optional()])

    frequency = SelectField('Frequência de Recorrência', choices=[
        ('', 'Não Recorrente'),
        ('daily', 'Diária'), 
        ('weekly', 'Semanal'), 
        ('monthly', 'Mensal'), 
        ('yearly', 'Anual')
    ], default='', validators=[Optional()])

    submit = SubmitField('Registrar Receita')
    
    def validate_receipt_date(self, field):
        try:
            num_repetitions = int(self.num_repetitions.data)
        except:
            num_repetitions = 0

        if num_repetitions > 0:
            return 
            
        if self.status.data == 'received':
            if not field.data:
                 raise ValidationError('A data de recebimento é obrigatória para receitas recebidas.')
            if field.data > date.today():
                 raise ValidationError('A data de recebimento não pode ser futura.')
    
    def validate_due_date(self, field):
        if field.data < self.date.data:
            raise ValidationError('A data de vencimento não pode ser anterior à data de registro.')
    
class ExpenseForm(FlaskForm):
    description = StringField('Descrição', validators=[
        DataRequired(), 
        Length(max=255)
    ])
    amount = DecimalField('Valor (R$)', validators=[
        DataRequired(), 
        NumberRange(min=0.01, message="O valor deve ser positivo.")
    ])
    
    due_date = DateField('Data de Vencimento', default=date.today, format='%Y-%m-%d', validators=[DataRequired()])
    date = DateField('Data de Lançamento', default=date.today, format='%Y-%m-%d', validators=[DataRequired()])

    status = SelectField('Situação', choices=[
        ('pending', 'A Pagar'), 
        ('paid', 'Pago')
    ], validators=[DataRequired()])
    
    payment_date = DateField('Data de Pagamento', format='%Y-%m-%d', validators=[Optional()])

    item = QuerySelectField(
        'Categoria de Despesa', # Label atualizado
        query_factory=get_user_expense_categories, # Função atualizada
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name, # Label simplificado (sem grupo)
        allow_blank=False,
        validators=[DataRequired(message="Selecione uma categoria de despesa.")]
    )
    
    wallet = QuerySelectField(
        'Carteira/Conta',
        query_factory=get_user_wallets,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
        validators=[DataRequired(message="Selecione uma carteira.")]
    )

    is_recurrent = BooleanField('Despesa Recorrente?')
    
    num_repetitions = SelectField('Repetir quantas vezes?', choices=[
        ('0', 'Apenas este lançamento'),
        ('1', '1 vez'),
        ('2', '2 vezes'), 
        ('3', '3 vezes'), 
        ('4', '4 vezes'), 
        ('5', '5 vezes'),
        ('6', '6 vezes'),
        ('7', '7 vezes'),
        ('8', '8 vezes'),
        ('9', '9 vezes'),
        ('10', '10 vezes'),
        ('11', '11 vezes')
    ], default='0', validators=[Optional()])
    
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

class TransferForm(FlaskForm):
    """Formulário para transferências entre carteiras."""
    amount = DecimalField('Valor da Transferência (R$)', validators=[
        DataRequired(), 
        NumberRange(min=0.01, message="O valor deve ser positivo.")
    ])
    
    source_wallet = QuerySelectField(
        'Carteira de Origem (Saída)',
        query_factory=get_user_wallets,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
        validators=[DataRequired(message="Selecione a carteira de onde o valor sairá.")]
    )
    
    target_wallet = QuerySelectField(
        'Carteira de Destino (Entrada)',
        query_factory=get_user_wallets,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
        validators=[DataRequired(message="Selecione a carteira para onde o valor irá.")]
    )
    
    submit = SubmitField('Confirmar Transferência')

    def validate_target_wallet(self, target_wallet):
        """Verifica se as carteiras de origem e destino são diferentes."""
        if self.source_wallet.data and target_wallet.data and self.source_wallet.data.id == target_wallet.data.id:
            raise ValidationError('A carteira de origem e a de destino devem ser diferentes.')
