from app.extensions import socketio, log
from app.constants import ACLPerformative, StandartAgent
from app.models import ACLMessage
from app.context import context
from app.events import SocketIOEventType, TriggerType
from app.services import chat_service
from .common import socketio_unicast

@socketio.on(SocketIOEventType.CHAT_REQUEST)
def handle_chat_request(req_json):
    chat_id = req_json.get('chat_id')
    try:
        chat_dto = chat_service.get_chat_dto_by_id(chat_id)
        if chat_dto:
            context.chat_id = chat_id
            socketio_unicast(SocketIOEventType.CHAT, {'status': 'success', 'chat': chat_dto.model_dump(mode='json')})
        else:
             raise ValueError(f"Chat with ID {chat_id} not found.")
    except Exception as e:
        log.exception(f"Error handling chat request for {chat_id}: {e}")
        socketio_unicast(SocketIOEventType.CHAT, {'status': 'error', 'message': str(e)})


@socketio.on(SocketIOEventType.CHAT_LIST_REQUEST)
def handle_chat_list_request():
    try:
        chat_ids = chat_service.get_all_chat_ids()
        socketio_unicast(SocketIOEventType.CHAT_LIST, {
            'status': 'success',
            'chat_ids': chat_ids
        })
    except Exception as e:
        log.exception(f"Error handling chat list request: {e}")
        socketio_unicast(SocketIOEventType.CHAT_LIST, {'status': 'error', 'message': str(e)})

@socketio.on(SocketIOEventType.NEW_CHAT_REQUEST)
def handle_new_chat_request(req_json: dict):
    try:
        card_id = req_json["card_id"]
        card_version = req_json["card_version"]
        chat_name = req_json.get("chat_name", "Chat")
        chat_dto = chat_service.create_new_chat(card_id=card_id, card_version=card_version, chat_name=chat_name)
        socketio_unicast(SocketIOEventType.NEW_CHAT, {
            'status': 'success',
            'chat_id': chat_dto.id
        })
    except Exception as e:
        log.exception(f"Error handling new chat request: {e}")
        socketio_unicast(SocketIOEventType.NEW_CHAT, {
            'status': 'error',
            'message': str(e)
        })


@socketio.on(SocketIOEventType.USER_MESSAGE_SEND)
def handle_user_message_send(msg_json, methods=['GET', 'POST']):
    try:
        chat_id = msg_json.pop('chat_id', None)
        if not chat_id:
             raise ValueError("Missing chat_id in user message send request")
        message_dto = chat_service.add_message_to_chat(chat_id=chat_id, message_data=msg_json)
        message_dict = message_dto.model_dump(mode='json')
        socketio_unicast(SocketIOEventType.MESSAGE_RECEIVED, {'status': 'success', 'message': message_dict})
        context.message_broker.publish(TriggerType.CHAT_MESSAGE_RECEIVED, ACLMessage(performative=ACLPerformative.INFORM, sender=StandartAgent.SYSTEM, content=message_dict))
    except Exception as e:
        log_chat_id = chat_id if 'chat_id' in locals() else msg_json.get('chat_id', 'unknown')
        log.exception(f"Error handling user message send for chat {log_chat_id}: {e}")
        socketio_unicast(SocketIOEventType.MESSAGE_RECEIVED, {'status': 'error', 'message': str(e)})


# @exception_logger
# @socketio.on(SocketIOEventType.SWIPE_REQUEST)
# def handle_swipe_request(req_json):
#     current_chat = get_current_chat(req_json['chat_id'])
#     current_chat.remove_last_message()
#     current_chat.save_chat()


# def handle_user_message_trigger(chat: Chat):
#     endpoint = 'endpoint'
#     api_key = 'api_key'
#     stream = True
#     messages = chat.get_linear_chat_from_message_id(chat.head)
#     model = 'gpt-4o-2024-11-20'
#     max_tokens = 4096
#     stop_sequences = []
#     temperature = 0.2
#     top_p = 1
#     top_k = 0
#     system = ''
#     for event in chat_completions_request('openai', endpoint=endpoint, api_key=api_key, messages=messages, model=model, max_tokens=max_tokens,
#                                         stop_sequences=stop_sequences, temperature=temperature, top_p=top_p, top_k=top_k, stream=stream, system=system):
#         event.handle()

#         if event.type == DataEventType.MESSAGE_START:
#             socketio_unicast(SocketIOEventType.MESSAGE_START)
#         elif event.type == DataEventType.MESSAGE_END:
#             socketio_unicast(SocketIOEventType.MESSAGE_END)
#         elif event.type == DataEventType.MESSAGE_DELTA:
#             socketio_unicast(SocketIOEventType.MESSAGE_DELTA, event.data)
#         elif event.type == DataEventType.STREAMED_MESSAGE_COMPLETE:
#             message = Message(role=MessageRole.ASSISTANT, content=event.data)
#             response_json = message.to_dict()
#             chat.add_message(response_json)
#             chat.save_chat()
#             socketio_unicast(SocketIOEventType.STREAMED_MESSAGE_RECEIVED, response_json)
#         elif event.type == DataEventType.MESSAGE_COMPLETE:
#             message = Message(role=MessageRole.ASSISTANT, content=event.data)
#             response_json = message.to_dict()
#             chat.add_message(response_json, chat.head)
#             chat.save_chat()
#             socketio_unicast(SocketIOEventType.MESSAGE_RECEIVED, response_json)
#         elif event.type == DataEventType.INFO:
#             log.warning(event.data)
#         elif event.type == DataEventType.ERROR:
#             socketio_unicast(SocketIOEventType.ERROR, event.data)
#             log.error(f'Error: {event.data}')

@socketio.on(SocketIOEventType.GET_MESSAGE_REQUEST)
def handle_get_message_request(req_json):
    message_id = req_json.get('id')
    chat_id = req_json.get('chat_id')
    try:
        message_dto = chat_service.get_message_dto_by_id(message_id)
        if not message_dto:
            raise ValueError(f"Message with ID {message_id} not found.")
        socketio_unicast(SocketIOEventType.GET_MESSAGE, {'status': 'success', 'message': message_dto.model_dump(mode='json')})
    except Exception as e:
        log.exception(f"Error handling get message request for chat {chat_id}, message {message_id}: {e}")
        socketio_unicast(SocketIOEventType.GET_MESSAGE, {'status': 'error', 'message': str(e)})


@socketio.on(SocketIOEventType.EDIT_MESSAGE_REQUEST)
def handle_edit_message_request(req_json):
    message_id = req_json.get('id')
    chat_id = req_json.get('chat_id')
    content = req_json.get('content')
    try:
        if not message_id or content is None:
             raise ValueError("Missing 'id' or 'content' in edit message request")
        chat_service.edit_message_content(message_id, content)
        socketio_unicast(SocketIOEventType.EDIT_MESSAGE, {'status': 'success', 'message_id': message_id})
    except Exception as e:
        log.exception(f"Error handling edit message request for chat {chat_id}, message {message_id}: {e}")
        socketio_unicast(SocketIOEventType.EDIT_MESSAGE, {'status': 'error', 'message': str(e), 'message_id': message_id})


@socketio.on(SocketIOEventType.REMOVE_MESSAGE_REQUEST)
def handle_remove_message_request(req_json):
    message_id = req_json.get('id')
    chat_id = req_json.get('chat_id')
    try:
        if not message_id or not chat_id:
             raise ValueError("Missing 'id' or 'chat_id' in remove message request")
        chat_service.remove_message_from_chat(chat_id, message_id)
        socketio_unicast(SocketIOEventType.REMOVE_MESSAGE, {'status': 'success', 'message_id': message_id})
    except Exception as e:
        log.exception(f"Error handling remove message request for chat {chat_id}, message {message_id}: {e}")
        socketio_unicast(SocketIOEventType.REMOVE_MESSAGE, {'status': 'error', 'message': str(e), 'message_id': message_id})


@socketio.on(SocketIOEventType.GET_OR_CREATE_LATEST_CHAT_REQUEST)
def handle_get_or_create_latest_chat_request(req_json: dict):
    """
    Handles the request to get or create the latest chat for a specific card.
    Expects 'card_id' and 'card_version' in the request JSON.
    Sends the chat object back on success or an error message on failure.
    """
    try:
        card_id = req_json["card_id"]
        card_version = req_json["card_version"]
        chat_dto = chat_service.get_or_create_latest_chat_for_card(card_id=card_id, card_version=card_version)
        socketio_unicast(SocketIOEventType.GET_OR_CREATE_LATEST_CHAT, {
            'status': 'success',
            'chat_id': chat_dto.id
        })
    except KeyError as e:
        log.error(f"Missing key in get_or_create_latest_chat request: {e}")
        socketio_unicast(SocketIOEventType.GET_OR_CREATE_LATEST_CHAT, {
            'status': 'error',
            'message': f"Missing required field: {e}"
        })
    except ValueError as e:
        log.error(f"Value error in get_or_create_latest_chat: {e}")
        socketio_unicast(SocketIOEventType.GET_OR_CREATE_LATEST_CHAT, {
            'status': 'error',
            'message': str(e)
        })
    except Exception as e:
        log.exception(f"Unexpected error in get_or_create_latest_chat: {e}")
        socketio_unicast(SocketIOEventType.GET_OR_CREATE_LATEST_CHAT, {
            'status': 'error',
            'message': f"An unexpected error occurred: {str(e)}"
        })

@socketio.on(SocketIOEventType.ADD_ATTACHMENT_REQUEST)
def handle_add_attachment_request(req_json: dict):
    message_id = req_json.get('message_id')
    filename = req_json.get('filename')
    content_base64 = req_json.get('content_base64')
    chat_id = req_json.get('chat_id')

    try:
        if not all([message_id, filename, content_base64]):
            raise ValueError("Missing 'message_id', 'filename', or 'content_base64' in add attachment request")
        
        attachment_dto = chat_service.add_attachment_to_message(
            message_id=message_id,
            filename=filename,
            content_base64=content_base64
        )
        socketio_unicast(SocketIOEventType.ADD_ATTACHMENT_RESPONSE, {
            'status': 'success',
            'attachment': attachment_dto.model_dump(mode='json')
        })
    except Exception as e:
        log.exception(f"Error handling add attachment request for message {message_id} in chat {chat_id}: {e}")
        socketio_unicast(SocketIOEventType.ADD_ATTACHMENT_RESPONSE, {
            'status': 'error',
            'message': str(e),
            'message_id': message_id
        })

@socketio.on(SocketIOEventType.REMOVE_ATTACHMENT_REQUEST)
def handle_remove_attachment_request(req_json: dict):
    attachment_id = req_json.get('attachment_id')
    message_id = req_json.get('message_id')
    chat_id = req_json.get('chat_id')

    try:
        if not attachment_id:
            raise ValueError("Missing 'attachment_id' in remove attachment request")
        
        chat_service.remove_attachment_from_message(attachment_id)
        socketio_unicast(SocketIOEventType.REMOVE_ATTACHMENT_RESPONSE, {
            'status': 'success',
            'attachment_id': attachment_id
        })
    except Exception as e:
        log.exception(f"Error handling remove attachment request for attachment {attachment_id} (message {message_id}, chat {chat_id}): {e}")
        socketio_unicast(SocketIOEventType.REMOVE_ATTACHMENT_RESPONSE, {
            'status': 'error',
            'message': str(e),
            'attachment_id': attachment_id
        })