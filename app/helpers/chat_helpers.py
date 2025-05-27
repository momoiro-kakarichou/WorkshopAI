from typing import List, Dict, Any, Optional
from app.context import context
from app.extensions import socketio, log
from app.constants import MessageRole
from app.events import SocketIOEventType
from app.services import chat_service
from app.dto.chat_dto import MessageDTO

def get_chat_history(chat_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieves the linear chat history for a given chat ID using the ChatService.

    Args:
        chat_id: The ID of the chat. If None, uses the chat_id from the context.

    Returns:
        A list of message dictionaries representing the linear history,
        or None if the chat is not found or an error occurs.
    """
    effective_chat_id = chat_id if chat_id is not None else context.chat_id
    if not effective_chat_id:
        log.warning("get_chat_history: No chat ID provided or found in context.")
        return None

    try:
        chat_dto = chat_service.get_chat_dto_by_id(effective_chat_id)
        if chat_dto:
            return [msg.model_dump(mode='json') for msg in chat_dto.messages]
        else:
            log.warning(f"get_chat_history: Chat {effective_chat_id} not found by service.")
            return None
    except Exception as e:
        log.exception(f"get_chat_history: Error retrieving history for chat {effective_chat_id}: {e}")
        return None

def add_one_message(content: str, role: str = MessageRole.ASSISTANT, chat_id: Optional[str] = None) -> Optional[MessageDTO]:
    """
    Adds a single message to the chat using the ChatService.

    Args:
        content: The message content.
        role: The role of the message sender.
        chat_id: The ID of the chat. If None, uses the chat_id from the context.

    Returns:
        The created MessageDTO, or None if an error occurs.
    """
    effective_chat_id = chat_id if chat_id is not None else context.chat_id
    if not effective_chat_id:
        log.warning("add_one_message: No chat ID provided or found in context.")
        return None

    try:
        message_data = {"role": role, "content": content}
        message_dto = chat_service.add_message_to_chat(chat_id=effective_chat_id, message_data=message_data)
        return message_dto
    except Exception as e:
        log.exception(f"add_one_message: Error adding message to chat {effective_chat_id}: {e}")
        return None
    
def add_one_message_and_notify(content: str, role: str = MessageRole.ASSISTANT, chat_id: Optional[str] = None):
    """Adds a message and notifies clients via SocketIO."""
    message_dto = add_one_message(content, role, chat_id)
    if message_dto:
        socketio.emit(SocketIOEventType.MESSAGE_RECEIVED, {'status': 'success', 'message': message_dto.model_dump(mode='json')})
            
def remove_last_message(chat_id: Optional[str] = None) -> bool:
    """Removes the last message (head) from the chat using ChatService."""
    effective_chat_id = chat_id if chat_id is not None else context.chat_id
    if not effective_chat_id:
        log.warning("remove_last_message: No chat ID provided or found in context.")
        return False

    try:
        chat_dto = chat_service.get_chat_dto_by_id(effective_chat_id)
        if not chat_dto:
             log.warning(f"remove_last_message: Chat {effective_chat_id} not found.")
             return False
        if not chat_dto.messages:
             log.warning(f"remove_last_message: Chat {effective_chat_id} has no messages.")
             return False
        message_id_to_remove = chat_dto.messages[-1].id

        chat_service.remove_message_from_chat(effective_chat_id, message_id_to_remove)
        return True
    except Exception as e:
        log.exception(f"remove_last_message: Error removing last message from chat {effective_chat_id}: {e}")
        return False
    
def remove_message_by_id(message_id: str, chat_id: Optional[str] = None) -> bool:
    """Removes a specific message from the chat using ChatService."""
    effective_chat_id = chat_id if chat_id is not None else context.chat_id
    if not effective_chat_id:
        log.warning("remove_message_by_id: No chat ID provided or found in context.")
        return False
    if not message_id:
        log.warning("remove_message_by_id: No message ID provided.")
        return False

    try:
        chat_service.remove_message_from_chat(effective_chat_id, message_id)
        return True
    except Exception as e:
        log.exception(f"remove_message_by_id: Error removing message {message_id} from chat {effective_chat_id}: {e}")
        return False

def get_last_message(chat_id: Optional[str] = None) -> Optional[Dict]:
    """Gets the last message (head) of the chat as a dictionary using ChatService."""
    effective_chat_id = chat_id if chat_id is not None else context.chat_id
    if not effective_chat_id:
        log.warning("get_last_message: No chat ID provided or found in context.")
        return None

    try:
        chat_dto = chat_service.get_chat_dto_by_id(effective_chat_id)
        if chat_dto and chat_dto.messages:
            last_message_dto = chat_dto.messages[-1]
            return last_message_dto.model_dump(mode='json')
        elif chat_dto:
             log.warning(f"get_last_message: Chat {effective_chat_id} found but has no messages.")
             return None
        else:
             log.warning(f"get_last_message: Chat {effective_chat_id} not found.")
             return None
    except Exception as e:
        log.exception(f"get_last_message: Error getting last message for chat {effective_chat_id}: {e}")
        return None
     
def get_message_by_id(message_id: str, chat_id: Optional[str] = None) -> Optional[Dict]:
    """Gets a specific message by ID as a dictionary using ChatService."""
    if not message_id:
        log.warning("get_message_by_id: No message ID provided.")
        return None

    try:
        message_dto = chat_service.get_message_dto_by_id(message_id)
        if message_dto:
            return message_dto.model_dump(mode='json')
        else:
            log.warning(f"get_message_by_id: Message {message_id} not found.")
            return None
    except Exception as e:
        log.exception(f"get_message_by_id: Error getting message {message_id}: {e}")
        return None

def edit_message_by_id(message_id: str, message_content: str, chat_id: Optional[str] = None) -> bool:
    """Edits a specific message's content using ChatService."""
    effective_chat_id = chat_id if chat_id is not None else context.chat_id
    if not message_id:
        log.warning("edit_message_by_id: No message ID provided.")
        return False
    if message_content is None:
        log.warning("edit_message_by_id: No message content provided.")
        return False

    try:
        chat_service.edit_message_content(message_id, message_content)
        return True
    except Exception as e:
        log.exception(f"edit_message_by_id: Error editing message {message_id} in chat {effective_chat_id}: {e}")
        return False
    
def get_message_var(message_id: str, key: str, default: Any = None) -> Any:
    """Gets a variable associated with a message using ChatService."""
    if not message_id or not key:
        log.warning("get_message_var: Missing message_id or key.")
        return default
    try:
        return chat_service.get_message_var(message_id, key, default)
    except Exception as e:
        log.exception(f"get_message_var: Error getting var '{key}' for message {message_id}: {e}")
        return default
    
def set_message_var(message_id: str, key: str, value: Any) -> bool:
    """Sets a variable for a message using ChatService."""
    if not message_id or not key:
        log.warning("set_message_var: Missing message_id or key.")
        return False
    try:
        chat_service.set_message_var(message_id, key, value)
        return True
    except Exception as e:
        log.exception(f"set_message_var: Error setting var '{key}' for message {message_id}: {e}")
        return False
    
def remove_message_var(message_id: str, key: str) -> bool:
    """Removes a variable from a message using ChatService."""
    if not message_id or not key:
        log.warning("remove_message_var: Missing message_id or key.")
        return False
    try:
        chat_service.remove_message_var(message_id, key)
        return True
    except Exception as e:
        log.exception(f"remove_message_var: Error removing var '{key}' for message {message_id}: {e}")
        return False