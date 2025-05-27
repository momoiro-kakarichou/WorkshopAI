import mimetypes
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from app.models.chat import Chat, Message, MessageVar, Attachment
from app.dao.card_dao import CardDAO
from app.dao.chat_dao import ChatDAO
from app.services import card_service
from app.dto.chat_dto import ChatDTO, MessageDTO, AttachmentDTO
from app.extensions import db
from app.context import context
from app.utils.utils import create_logger

chat_service_log = create_logger(__name__, entity_name='CHAT_SERVICE', level=context.log_level)

def _map_attachment_model_to_dto(attachment: Attachment, include_content: bool = False) -> AttachmentDTO:
    """Maps an Attachment SQLAlchemy model to an AttachmentDTO."""
    dto = AttachmentDTO(
        id=attachment.id,
        message_id=attachment.message_id,
        filename=attachment.filename,
        attachment_type=attachment.attachment_type,
        creation_time=attachment.creation_time.isoformat()
    )
    if include_content:
        dto.content_base64 = attachment.content_base64
    return dto

def _map_message_model_to_dto(message: Message) -> MessageDTO:
    """Maps a Message SQLAlchemy model to a MessageDTO."""
    card_name = None
    card_avatar_uri = None
    if message.card:
        card_name = message.card.name
        try:
            card_avatar_uri = card_service.get_card_avatar_url(message.card.id, message.card.version)
        except Exception as e:
            chat_service_log.warning(f"ChatService: Failed to get avatar for card {message.card.id}_{message.card.version} via service: {e}")
            card_avatar_uri = card_service._get_default_avatar_url()
    
    attachment_dtos = [_map_attachment_model_to_dto(att) for att in message.attachments]

    return MessageDTO(
        id=message.id,
        chat_id=message.chat_id,
        parent_id=message.parent_id,
        depth=message.depth,
        role=message.role,
        creation_time=message.creation_time.isoformat(),
        modification_time=message.modification_time.isoformat(),
        card_id=message.card_id,
        card_version=message.card_version,
        card_name=card_name,
        card_avatar_uri=card_avatar_uri,
        content=message.content,
        vars={var.key: var.value for var in message.variables},
        attachments=attachment_dtos
    )

def _get_linear_chat_history_models(chat: Chat, head_message_id: Optional[str]) -> List[Message]:
    """Retrieves the linear history of message models up to the head."""
    if not head_message_id:
        return []

    message_map = {msg.id: msg for msg in chat.messages}
    linear_chat_models = []
    current_message_id = head_message_id

    while current_message_id and current_message_id in message_map:
        message = message_map[current_message_id]
        linear_chat_models.append(message)
        current_message_id = message.parent_id

    linear_chat_models.reverse()
    return linear_chat_models


def get_chat_dto_by_id(chat_id: str) -> Optional[ChatDTO]:
    """
    Retrieves a chat by its ID and returns it as a ChatDTO,
    including its linear message history based on the head.
    """
    chat = ChatDAO.get_chat_by_id(chat_id)
    if not chat:
        chat_service_log.warning(f"ChatService: Chat with ID {chat_id} not found in DAO.")
        return None

    linear_history_models = _get_linear_chat_history_models(chat, chat.head)
    message_dtos = [_map_message_model_to_dto(msg) for msg in linear_history_models]

    return ChatDTO(
        id=chat.id,
        name=chat.name,
        messages=message_dtos
    )

def get_all_chat_ids() -> List[str]:
    """Retrieves a list of all chat IDs."""
    return ChatDAO.get_all_chat_ids()

def create_new_chat(card_id: str, card_version: str, chat_name: str) -> ChatDTO:
    """Creates a new chat associated with a card."""
    card = CardDAO.get_card_by_primary_key(id=card_id, version=card_version)
    if not card:
        chat_service_log.error(f"ChatService: Card with ID {card_id} and version {card_version} not found.")
        raise ValueError(f"Card with ID {card_id} and version {card_version} not found.")

    try:
        new_chat_model = ChatDAO.create_chat(name=chat_name, card=card)
        db.session.commit()
        chat_service_log.info(f"ChatService: Created new chat {new_chat_model.id} for card {card_id} v{card_version}.")
        return ChatDTO(
            id=new_chat_model.id,
            name=new_chat_model.name,
            messages=[]
        )
    except Exception as e:
        db.session.rollback()
        chat_service_log.error(f"ChatService: Error creating chat for card {card_id} v{card_version}: {e}", exc_info=True)
        raise

def get_or_create_latest_chat_for_card(card_id: str, card_version: str) -> ChatDTO:
    """
    Gets the latest chat for a card or creates a new one if none exists.
    Returns the chat as a ChatDTO.
    """
    latest_chat_model = ChatDAO.find_latest_chat_for_card(card_id, card_version)

    if latest_chat_model:
        chat_service_log.info(f"ChatService: Found latest chat {latest_chat_model.id} for card {card_id} v{card_version}.")
        linear_history_models = _get_linear_chat_history_models(latest_chat_model, latest_chat_model.head)
        message_dtos = [_map_message_model_to_dto(msg) for msg in linear_history_models]
        return ChatDTO(
            id=latest_chat_model.id,
            name=latest_chat_model.name,
            messages=message_dtos
        )
    else:
        chat_service_log.info(f"ChatService: No chat found for card {card_id} v{card_version}. Creating new one.")
        card = CardDAO.get_card_by_primary_key(id=card_id, version=card_version)
        if not card:
            chat_service_log.error(f"ChatService: Card with ID {card_id} and version {card_version} not found during get_or_create.")
            raise ValueError(f"Card with ID {card_id} and version {card_version} not found.")
        chat_name = f"Chat with {card.name}"
        return create_new_chat(card_id, card_version, chat_name)


def add_message_to_chat(chat_id: str, message_data: Dict[str, Any], parent_id: Optional[str] = None) -> MessageDTO:
    """Adds a new message to a chat and updates the chat's head."""
    chat = ChatDAO.get_chat_by_id(chat_id)
    if not chat:
        chat_service_log.error(f"ChatService: Cannot add message, chat {chat_id} not found.")
        raise ValueError(f"Chat with ID {chat_id} not found.")

    depth = 0
    if parent_id:
        parent_message = ChatDAO.get_message_by_id(parent_id)
        if not parent_message or parent_message.chat_id != chat_id:
            chat_service_log.error(f"ChatService: Parent message {parent_id} not found or not in chat {chat_id}.")
            raise ValueError(f"Parent message with ID {parent_id} not found in chat {chat_id}.")
        depth = parent_message.depth + 1
    elif chat.head:
        parent_id = chat.head
        parent_message = ChatDAO.get_message_by_id(parent_id)
        if parent_message:
             depth = parent_message.depth + 1
        else:
             chat_service_log.warning(f"ChatService: Chat head {chat.head} points to non-existent message for chat {chat_id}. Setting depth 0.")
             parent_id = None

    core_fields = {k: v for k, v in message_data.items() if k in Message.__table__.columns.keys()}
    vars_data = message_data.get('vars', {})

    new_message = Message(
        chat_id=chat_id,
        parent_id=parent_id,
        depth=depth,
        **core_fields
    )

    for key, value in vars_data.items():
         new_message.variables.append(MessageVar(key=key, value=value))

    try:
        saved_message = ChatDAO.save_message(new_message)
        db.session.flush()

        db.session.add(chat)
        chat.head = saved_message.id
        chat.modification_time = datetime.now(timezone.utc)

        db.session.commit()
        db.session.refresh(chat)
        chat_service_log.info(f"ChatService: Added message {saved_message.id} to chat {chat_id}. New head: {chat.head}.")
        return _map_message_model_to_dto(saved_message)
    except Exception as e:
        db.session.rollback()
        chat_service_log.error(f"ChatService: Error adding message to chat {chat_id}: {e}", exc_info=True)
        raise


def get_message_dto_by_id(message_id: str) -> Optional[MessageDTO]:
    """Retrieves a message by its ID and returns it as a MessageDTO."""
    message = ChatDAO.get_message_by_id(message_id)
    if not message:
        chat_service_log.warning(f"ChatService: Message with ID {message_id} not found.")
        return None
    return _map_message_model_to_dto(message)

def edit_message_content(message_id: str, new_content: str) -> MessageDTO:
    """Edits the content of an existing message."""
    message = ChatDAO.get_message_by_id(message_id)
    if not message:
        chat_service_log.error(f"ChatService: Cannot edit message, ID {message_id} not found.")
        raise ValueError(f"Message with ID {message_id} not found.")

    message.content = new_content
    try:
        db.session.add(message)
        saved_message = message

        chat = ChatDAO.get_chat_by_id(message.chat_id)
        if chat:
            db.session.add(chat)
            chat.modification_time = datetime.now(timezone.utc)

        db.session.commit()
        chat_service_log.info(f"ChatService: Edited content for message {message_id}.")
        return _map_message_model_to_dto(saved_message)
    except Exception as e:
        db.session.rollback()
        chat_service_log.error(f"ChatService: Error editing message {message_id}: {e}", exc_info=True)
        raise

def remove_message_from_chat(chat_id: str, message_id: str):
    """Removes a message and potentially reparents its children."""
    chat = ChatDAO.get_chat_by_id(chat_id)
    if not chat:
        chat_service_log.error(f"ChatService: Cannot remove message, chat {chat_id} not found.")
        raise ValueError(f"Chat with ID {chat_id} not found.")

    message_to_remove = ChatDAO.get_message_by_id(message_id)
    if not message_to_remove or message_to_remove.chat_id != chat_id:
        chat_service_log.error(f"ChatService: Message {message_id} not found or not in chat {chat_id}.")
        raise ValueError(f"Message with ID {message_id} not found in chat {chat_id}.")

    new_parent_id = message_to_remove.parent_id
    children = ChatDAO.get_messages_by_parent_id(message_id)

    try:
        db.session.add(chat)
        db.session.add(message_to_remove)

        for child in children:
            db.session.add(child)
            child.parent_id = new_parent_id
            child.depth = max(0, child.depth - 1)

        if chat.head == message_id:
            chat.head = new_parent_id
            chat.modification_time = datetime.now(timezone.utc)

        ChatDAO.delete_message(message_to_remove)

        db.session.commit()
        chat_service_log.info(f"ChatService: Removed message {message_id} from chat {chat_id}. Reparented {len(children)} children to {new_parent_id}. New head: {chat.head}.")
    except Exception as e:
        db.session.rollback()
        chat_service_log.error(f"ChatService: Error removing message {message_id} from chat {chat_id}: {e}", exc_info=True)
        raise

def get_message_var(message_id: str, key: str, default: Any = None) -> Any:
    """Gets a variable associated with a message."""
    message_var = ChatDAO.get_message_var(message_id, key)
    return message_var.value if message_var else default

def set_message_var(message_id: str, key: str, value: Any):
    """Sets a variable for a message, creating or updating it."""
    message = ChatDAO.get_message_by_id(message_id)
    if not message:
        raise ValueError(f"Message with ID {message_id} not found.")

    try:
        message_var = ChatDAO.get_message_var(message_id, key)
        if message_var:
            db.session.add(message_var)
            message_var.value = value
        else:
            new_var = MessageVar(message_id=message_id, key=key, value=value)
            ChatDAO.save_message_var(new_var)

        db.session.commit()
        chat_service_log.info(f"ChatService: Set variable '{key}' for message {message_id}.")
    except Exception as e:
        db.session.rollback()
        chat_service_log.error(f"ChatService: Error setting variable '{key}' for message {message_id}: {e}", exc_info=True)
        raise


def remove_message_var(message_id: str, key: str):
    """Removes a variable from a message."""
    message_var = ChatDAO.get_message_var(message_id, key)
    if message_var:
        try:
            ChatDAO.delete_message_var(message_var)
            db.session.commit()
            chat_service_log.info(f"ChatService: Removed variable '{key}' from message {message_id}.")
        except Exception as e:
            db.session.rollback()
            chat_service_log.error(f"ChatService: Error removing variable '{key}' from message {message_id}: {e}", exc_info=True)
            raise
    else:
        chat_service_log.warning(f"ChatService: Variable '{key}' not found for message {message_id}, cannot remove.")
        
def swipe_message_in_chat(chat_id: str, message_data: Dict[str, Any]) -> MessageDTO:
    """
    Performs a 'swipe' operation: moves the head to its parent,
    then adds a new message at the same depth as the original head.
    """
    chat = ChatDAO.get_chat_by_id(chat_id)
    if not chat:
        chat_service_log.error(f"ChatService: Cannot swipe message, chat {chat_id} not found.")
        raise ValueError(f"Chat with ID {chat_id} not found.")

    if not chat.head:
        chat_service_log.error(f"ChatService: Cannot swipe message, chat {chat_id} has no head.")
        raise ValueError(f"Chat {chat_id} has no head message to swipe.")

    original_head_message = ChatDAO.get_message_by_id(chat.head)
    if not original_head_message:
        chat_service_log.error(f"ChatService: Chat head {chat.head} points to non-existent message for chat {chat_id}. Cannot swipe.")
        raise ValueError(f"Chat head {chat.head} for chat {chat_id} is invalid.")

    new_head_id = original_head_message.parent_id
    new_depth = original_head_message.depth

    core_fields = {k: v for k, v in message_data.items() if k in Message.__table__.columns.keys()}
    vars_data = message_data.get('vars', {})

    new_message = Message(
        chat_id=chat_id,
        parent_id=new_head_id,
        depth=new_depth,
        **core_fields
    )

    for key, value in vars_data.items():
         new_message.variables.append(MessageVar(key=key, value=value))

    try:
        saved_message = ChatDAO.save_message(new_message)
        db.session.flush()

        db.session.add(chat)
        chat.head = saved_message.id
        chat.modification_time = datetime.now(timezone.utc)

        db.session.commit()
        db.session.refresh(chat)
        db.session.refresh(saved_message)

        chat_service_log.info(f"ChatService: Swiped message in chat {chat_id}. Original head was {original_head_message.id}. New head: {saved_message.id}.")
        return _map_message_model_to_dto(saved_message)
    except Exception as e:
        db.session.rollback()
        chat_service_log.error(f"ChatService: Error swiping message in chat {chat_id}: {e}", exc_info=True)
        raise
    
def move_chat_head_up(chat_id: str) -> Optional[ChatDTO]:
    """Moves the chat head pointer one message up the linear history (towards the root)."""
    chat = ChatDAO.get_chat_by_id(chat_id)
    if not chat:
        chat_service_log.error(f"ChatService: Cannot move head up, chat {chat_id} not found.")
        raise ValueError(f"Chat with ID {chat_id} not found.")

    if not chat.head:
        chat_service_log.warning(f"ChatService: Chat {chat_id} has no head message, cannot move up.")
        linear_history_models = _get_linear_chat_history_models(chat, chat.head)
        message_dtos = [_map_message_model_to_dto(msg) for msg in linear_history_models]
        return ChatDTO(id=chat.id, name=chat.name, messages=message_dtos)

    head_message = ChatDAO.get_message_by_id(chat.head)
    if not head_message:
        chat_service_log.error(f"ChatService: Chat head {chat.head} points to non-existent message for chat {chat_id}. Cannot move up.")
        raise ValueError(f"Chat head {chat.head} for chat {chat_id} is invalid.")

    new_head_id = head_message.parent_id

    try:
        db.session.add(chat)
        chat.head = new_head_id
        chat.modification_time = datetime.now(timezone.utc)
        db.session.commit()
        db.session.refresh(chat)

        chat_service_log.info(f"ChatService: Moved head for chat {chat_id} up to message {new_head_id}.")

        updated_linear_history_models = _get_linear_chat_history_models(chat, chat.head)
        updated_message_dtos = [_map_message_model_to_dto(msg) for msg in updated_linear_history_models]

        return ChatDTO(
            id=chat.id,
            name=chat.name,
            messages=updated_message_dtos
        )
    except Exception as e:
        db.session.rollback()
        chat_service_log.error(f"ChatService: Error moving head up for chat {chat_id}: {e}", exc_info=True)
        raise

def get_head_message_dto(chat_id: str) -> Optional[MessageDTO]:
    """Retrieves the head message of a chat as a MessageDTO."""
    chat = ChatDAO.get_chat_by_id(chat_id)
    if not chat:
        chat_service_log.warning(f"ChatService: Chat {chat_id} not found when trying to get head message.")
        return None
    if not chat.head:
        chat_service_log.warning(f"ChatService: Chat {chat_id} has no head message.")
        return None
    
    head_message = ChatDAO.get_message_by_id(chat.head)
    if not head_message:
        chat_service_log.warning(f"ChatService: Head message ID {chat.head} for chat {chat_id} not found.")
        return None
    return _map_message_model_to_dto(head_message)

def add_attachment_to_message(message_id: str, filename: str, content_base64: str) -> AttachmentDTO:
    """Adds an attachment to a message."""
    message = ChatDAO.get_message_by_id(message_id)
    if not message:
        chat_service_log.error(f"ChatService: Cannot add attachment, message {message_id} not found.")
        raise ValueError(f"Message with ID {message_id} not found.")

    attachment_type, _ = mimetypes.guess_type(filename)
    if not attachment_type:
        attachment_type = "application/octet-stream"
        chat_service_log.warning(f"ChatService: Could not determine MIME type for {filename}, defaulting to {attachment_type}.")


    new_attachment = Attachment(
        message_id=message_id,
        filename=filename,
        content_base64=content_base64,
        attachment_type=attachment_type
    )

    try:
        ChatDAO.save_attachment(new_attachment)
        db.session.commit()
        db.session.refresh(new_attachment)
        chat_service_log.info(f"ChatService: Added attachment {new_attachment.id} to message {message_id}.")
        return _map_attachment_model_to_dto(new_attachment, include_content=True)
    except Exception as e:
        db.session.rollback()
        chat_service_log.error(f"ChatService: Error adding attachment to message {message_id}: {e}", exc_info=True)
        raise

def remove_attachment_from_message(attachment_id: str):
    """Removes an attachment from a message."""
    attachment = ChatDAO.get_attachment_by_id(attachment_id)
    if not attachment:
        chat_service_log.error(f"ChatService: Cannot remove attachment, ID {attachment_id} not found.")
        raise ValueError(f"Attachment with ID {attachment_id} not found.")

    try:
        ChatDAO.delete_attachment(attachment)
        db.session.commit()
        chat_service_log.info(f"ChatService: Removed attachment {attachment_id}.")
    except Exception as e:
        db.session.rollback()
        chat_service_log.error(f"ChatService: Error removing attachment {attachment_id}: {e}", exc_info=True)
        raise