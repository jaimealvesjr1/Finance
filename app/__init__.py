from flask import Flask
from config import Config
from .extensions import db, login_manager, migrate, scheduler
import os

from .auth import models as auth_models
from .financeiro import models as financeiro_models

from .auth.routes import auth_bp
from .main.routes import main_bp
from .financeiro.routes import financeiro_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    scheduler.init_app(app)

    from flask import get_flashed_messages
    @app.context_processor
    def inject_flashes():
        return dict(get_flashed_messages=get_flashed_messages)

    @login_manager.user_loader
    def load_user(user_id):
        from .auth.models import User
        return User.query.get(int(user_id))
    
    @scheduler.task('interval', id='recorrencia_check', minutes=30)
    def job_process_recorrencia():
        with app.app_context():
            from .financeiro.tasks import process_recurrent_transactions
            process_recurrent_transactions()
    
    scheduler.start()

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(financeiro_bp)

    return app
