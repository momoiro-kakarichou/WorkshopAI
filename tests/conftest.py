import pytest
from app import create_app
from app.extensions import db
from config import FlaskTestingConfig
            
@pytest.fixture(scope='module')
def app():
    flask_app = create_app(FlaskTestingConfig)
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='module')
def test_client(app):
    return app.test_client()
