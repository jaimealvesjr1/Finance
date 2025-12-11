from flask import Flask, session
from config import Config
from .extensions import db, login_manager, migrate, scheduler
import os
from decimal import Decimal

from .auth import models as auth_models
from .financeiro import models as financeiro_models

from .auth.routes import auth_bp
from .main.routes import main_bp
from .financeiro.routes import financeiro_bp
from .admin.routes import admin_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    scheduler.init_app(app)

    @app.template_filter('currency')
    def format_currency(value):
        if value is None:
            return 'R$ 0,00'
        
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        return f"R$ {value:,.2f}".replace(",", "V").replace(".", ",").replace("V", ".")

    from flask import get_flashed_messages
    @app.context_processor
    def inject_flashes():
        return dict(get_flashed_messages=get_flashed_messages)

    @login_manager.user_loader
    def load_user(user_id):
        from .auth.models import User
        return User.query.get(int(user_id))
    
    @app.before_request
    def check_access_status():
        from flask_login import current_user, logout_user
        from flask import url_for, redirect, flash, request
        
        if current_user.is_authenticated and request.endpoint and not request.blueprint in ['auth']:
            
            if not current_user.is_active and not current_user.is_admin:
                
                if request.endpoint not in ['auth.profile', 'auth.logout']:
                    flash('Seu acesso está suspenso. Renove sua assinatura na tela de perfil.', 'danger')
                    return redirect(url_for('auth.profile'))
            
            if current_user.pending_message:
                message = current_user.pending_message
                flash(f'Mensagem do Administrador: {message}', 'warning')
                
                current_user.pending_message = None 
                db.session.commit()
                
                return redirect(url_for(request.endpoint, **request.args))
    
    @scheduler.task('interval', id='recorrencia_check', minutes=30)
    def job_process_recorrencia():
        with app.app_context():
            from .financeiro.tasks import process_recurrent_transactions
            process_recurrent_transactions()
    
    scheduler.start()

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(admin_bp)

    return app
