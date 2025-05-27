import pytest
from app.extensions import socketio

@pytest.fixture(scope='module')
def socketio_client(app, test_client):
    return socketio.test_client(app, flask_test_client=test_client)

def test_socketio_connection(socketio_client):
    assert socketio_client.is_connected()

def test_socketio_event(socketio_client):
    socketio_client.emit('my_event', {'data': 'test'})
    received = socketio_client.get_received()
    assert received[0]['name'] == 'my_response'
    assert received[0]['args'][0]['data'] == 'test'