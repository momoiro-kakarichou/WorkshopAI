import os
import logging
from flask import Flask
from flask_assets import Environment, Bundle
from config import FlaskConfig
from app.context import context
from app.extensions import db, migrate, socketio, log

def create_app(config=FlaskConfig):
    app = Flask(__name__)
    app.config.from_object(config)
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    context.cyclic_task_manager.init_app(app)
    
    app_log_level_str = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    flask_log_level_str = os.getenv("FLASK_LOG_LEVEL", "WARNING").upper()
    log_level_map = logging.getLevelNamesMapping()
    
    context.log_level = log_level_map.get(app_log_level_str, logging.INFO)
    log.setLevel(log_level_map.get(flask_log_level_str, logging.WARNING))

    assets = Environment(app)

    js_external = Bundle(
        'scripts/external/socket.io.min.js',
        'scripts/external/jquery-3.7.1.min.js',
        'scripts/external/jquery-ui.min.js',
        'scripts/external/marked.min.js',
        'scripts/external/highlight.min.js',
        'scripts/external/codemirror.min.js',
        'scripts/external/python.min.js',
        'scripts/external/joint.js',
        'scripts/external/quill.js',
        'scripts/external/toastr.min.js',
        'scripts/external/bootstrap.min.js',
        'scripts/external/popper.min.js',
        'scripts/external/select2.min.js',
        output='gen/external.js'
    )

    assets.register('js_external', js_external)

    css_external = Bundle(
        'styles/external/github-dark.min.css',
        'styles/external/quill.snow.css',
        'styles/external/bootstrap-icons.min.css',
        'styles/external/fontawesome.min.css',
        'styles/external/theme.min.css',
        'styles/external/jquery-ui.min.css',
        'styles/external/codemirror.min.css',
        'styles/external/bootstrap.min.css',
        'styles/external/select2.min.css',
        'styles/external/toastr.min.css',
        'styles/solid.min.css',
        'styles/brands.min.css',
        output='gen/external.css'
    )

    css_internal = Bundle(
        'styles/index.css',
        'styles/editors.css',
        output='gen/internal.css'
    )

    assets.register('css_external', css_external)
    assets.register('css_internal', css_internal)

    from . import models, socket_handlers, runtime_services
    models.init_app(app, context)
    runtime_services.init_app(app, context)
    socket_handlers.init_app(app)
    
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    return app