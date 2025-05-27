from flask import request
from app.extensions import socketio

def socketio_unicast(event, data=None, **kwargs):
    if 'to' not in kwargs:
        kwargs['to'] = request.sid
    socketio.emit(event, data, **kwargs)

def socketio_broadcast(event, data=None, **kwargs):
    socketio.emit(event, data, **kwargs)
    