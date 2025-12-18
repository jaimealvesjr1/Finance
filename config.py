import os
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mrjrivalbusiness'
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'site.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    TIMEZONE = 'America/Sao_Paulo'
    VERSAO_APP = 'Beta 1.1'
    ANO_ATUAL = datetime.now().year
    
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads', 'profile_pics')
    