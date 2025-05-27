from typing import List, Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload
from app.extensions import db
from app.models.chat import Chat, Message, MessageVar, Attachment
from app.models.card import Card
from app.utils.utils import create_logger
from app.context import context

chat_dao_log = create_logger(__name__, entity_name='CHAT_DAO', level=context.log_level)

class ChatDAO:
    """Data Access Object for Chat and Message operations."""

    @staticmethod
    def _get_session(session: Optional[Session] = None) -> Session:
        """Gets the current session or the default one."""
        return session or db.session

    @staticmethod
    def get_message_by_id(message_id: str, session: Optional[Session] = None) -> Optional[Message]:
        """Retrieves a message by its ID."""
        current_session = ChatDAO._get_session(session)
        stmt = select(Message).options(
            selectinload(Message.variables),
            selectinload(Message.attachments)
        ).where(Message.id == message_id)
        return current_session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_messages_by_parent_id(parent_id: str, session: Optional[Session] = None) -> List[Message]:
        """Retrieves all messages with a specific parent ID."""
        current_session = ChatDAO._get_session(session)
        stmt = select(Message).where(Message.parent_id == parent_id).options(
            selectinload(Message.variables),
            selectinload(Message.attachments)
        )
        return current_session.execute(stmt).scalars().all()

    @staticmethod
    def save_message(message: Message, session: Optional[Session] = None) -> Message:
        """Adds or updates a message in the session (no commit)."""
        current_session = ChatDAO._get_session(session)
        current_session.add(message)
        return message

    @staticmethod
    def delete_message(message: Message, session: Optional[Session] = None):
        """Marks a message for deletion (no commit)."""
        current_session = ChatDAO._get_session(session)
        current_session.delete(message)

    @staticmethod
    def get_message_var(message_id: str, key: str, session: Optional[Session] = None) -> Optional[MessageVar]:
        """Gets a MessageVar object by message_id and key."""
        current_session = ChatDAO._get_session(session)
        stmt = select(MessageVar).where(MessageVar.message_id == message_id, MessageVar.key == key)
        return current_session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def save_message_var(message_var: MessageVar, session: Optional[Session] = None):
        """Adds or updates a MessageVar object in the session (no commit)."""
        current_session = ChatDAO._get_session(session)
        current_session.add(message_var)

    @staticmethod
    def delete_message_var(message_var: MessageVar, session: Optional[Session] = None):
        """Marks a MessageVar object for deletion (no commit)."""
        current_session = ChatDAO._get_session(session)
        current_session.delete(message_var)

    @staticmethod
    def get_chat_by_id(chat_id: str, session: Optional[Session] = None) -> Optional[Chat]:
        """Retrieves a chat by its ID, eagerly loading messages and associated cards."""
        current_session = ChatDAO._get_session(session)
        stmt = select(Chat).options(
            selectinload(Chat.messages).options(
                selectinload(Message.variables),
                selectinload(Message.attachments)
            ),
            selectinload(Chat.cards)
        ).where(Chat.id == chat_id)
        return current_session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_all_chat_ids(session: Optional[Session] = None) -> List[str]:
        """Retrieves a list of all chat IDs."""
        current_session = ChatDAO._get_session(session)
        stmt = select(Chat.id)
        return [chat_id for chat_id, in current_session.execute(stmt).all()]

    @staticmethod
    def save_chat(chat: Chat, session: Optional[Session] = None) -> Chat:
        """Adds or updates a chat in the session (no commit)."""
        current_session = ChatDAO._get_session(session)
        current_session.add(chat)
        return chat

    @staticmethod
    def delete_chat(chat: Chat, session: Optional[Session] = None):
        """Marks a chat for deletion (no commit)."""
        current_session = ChatDAO._get_session(session)
        current_session.delete(chat)

    @staticmethod
    def find_latest_chat_for_card(card_id: str, card_version: str, session: Optional[Session] = None) -> Optional[Chat]:
        """Finds the most recently modified chat associated with a specific card version."""
        current_session = ChatDAO._get_session(session)
        stmt = select(Chat) \
            .join(Chat.cards) \
            .where(Card.id == card_id, Card.version == card_version) \
            .order_by(desc(Chat.modification_time)) \
            .limit(1)
        return current_session.execute(stmt).unique().scalar_one_or_none()

    @staticmethod
    def create_chat(name: str, card: Card, session: Optional[Session] = None) -> Chat:
        """Creates a new Chat instance, associates it with a card, adds to session (no commit)."""
        current_session = ChatDAO._get_session(session)
        if card not in current_session and card.id is not None:
             card = current_session.merge(card)
        elif card not in current_session:
             current_session.add(card)

        new_chat = Chat(name=name)
        new_chat.cards.append(card)
        current_session.add(new_chat)
        return new_chat

    @staticmethod
    def get_attachment_by_id(attachment_id: str, session: Optional[Session] = None) -> Optional[Attachment]:
        """Retrieves an attachment by its ID."""
        current_session = ChatDAO._get_session(session)
        stmt = select(Attachment).where(Attachment.id == attachment_id)
        return current_session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def save_attachment(attachment: Attachment, session: Optional[Session] = None) -> Attachment:
        """Adds or updates an attachment in the session (no commit)."""
        current_session = ChatDAO._get_session(session)
        current_session.add(attachment)
        return attachment

    @staticmethod
    def delete_attachment(attachment: Attachment, session: Optional[Session] = None):
        """Marks an attachment for deletion (no commit)."""
        current_session = ChatDAO._get_session(session)
        current_session.delete(attachment)