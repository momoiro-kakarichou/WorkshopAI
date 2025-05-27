import logging
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()
log = logging.getLogger('werkzeug')