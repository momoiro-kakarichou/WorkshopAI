from app.events import SocketIOEventType
from app.extensions import socketio
from .common import socketio_unicast
from .api import *
from .chat import *
from .workflow import *
from .agent import *
from .card import *

def init_app(app):
    pass

@socketio.on(SocketIOEventType.CONNECT)
def handle_connect():
    pass

@socketio.on(SocketIOEventType.PING)
def handle_ping():
    socketio_unicast(SocketIOEventType.PONG)
    
# @socketio.on(SocketIOEventType.MESSAGE_FROM_INTERFACE_AGENT)
# def handle_message_from_interface_agent(message_json: dict):
#     if ACLMessage.validate_dict_message(message_json):
#         message = ACLMessage.from_dict(message_json)
#         if message.receiver:
#             ACLRouter.unicast(message)
#         else:
#             ACLRouter.broadcast(message)