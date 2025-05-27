import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.constants import MessageRole
from app.extensions import db
from app.models import Card
# Removed unused db utils: commit_changes, add_and_commit, get_all_entity_ids, delete_entity, get_entity_by_key
# Removed unused sqlalchemy import: desc

@dataclass
class Message(db.Model):
    __tablename__ = 'messages'
    
    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id: Mapped[str] = mapped_column(db.String, db.ForeignKey('chats.id'), nullable=False, index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(db.String, db.ForeignKey('messages.id'), nullable=True, index=True)
    depth: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    role: Mapped[str] = mapped_column(db.String(50), nullable=False, default=MessageRole.NONE)
    creation_time: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    modification_time: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    content: Mapped[str] = mapped_column(db.Text, nullable=False, default='')
    card_id: Mapped[str] = mapped_column(db.String, nullable=True)
    card_version: Mapped[str] = mapped_column(db.String, nullable=True)
    
    card: Mapped[Optional[Card]] = relationship(
        'Card',
        foreign_keys=[card_id, card_version],
        primaryjoin='and_(Message.card_id == Card.id, Message.card_version == Card.version)',
        lazy='select'
    )
    variables: Mapped[List['MessageVar']] = relationship(
        'MessageVar',
        back_populates='message',
        cascade='all, delete-orphan',
        lazy='selectin'
    )
    attachments: Mapped[List['Attachment']] = relationship(
        'Attachment',
        back_populates='message',
        cascade='all, delete-orphan',
        lazy='selectin'
    )

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['card_id', 'card_version'],
            ['cards.id', 'cards.version'],
            name='message_card_fk'
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        card_name = None
        card_avatar_uri = None
        if self.card:
            card_name = self.card.name
            card_avatar_uri = self.card.get_card_avatar()

        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'parent_id': self.parent_id,
            'depth': self.depth,
            'role': self.role,
            'creation_time': self.creation_time.isoformat(),
            'modification_time': self.modification_time.isoformat(),
            'card_id': self.card_id,
            'card_version': self.card_version,
            'card_name': card_name,
            'card_avatar_uri': card_avatar_uri,
            'content': self.content,
            'vars': {var.key: var.value for var in self.variables},
            'attachments': [attachment.to_dict() for attachment in self.attachments]
        }

    # Methods get_var, set_var, update_vars_by_dict, remove_var, save_message, get_message_by_id moved to DAO/Service


@dataclass
class MessageVar(db.Model):
    __tablename__ = 'message_vars'

    key: Mapped[str] = mapped_column(db.String, nullable=False, primary_key=True)
    value: Mapped[Optional[Any]] = mapped_column(db.JSON, nullable=True)
    message_id: Mapped[str] = mapped_column(db.String, db.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True)

    message: Mapped['Message'] = relationship(back_populates='variables')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'value': self.value
        }


@dataclass
class Attachment(db.Model):
    __tablename__ = 'attachments'

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id: Mapped[str] = mapped_column(db.String, db.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(db.String, nullable=False)
    content_base64: Mapped[str] = mapped_column(db.Text, nullable=False) # Storing as TEXT, consider LargeBinary if storing raw bytes
    attachment_type: Mapped[Optional[str]] = mapped_column(db.String, nullable=True) # e.g., 'image/png', 'application/pdf'
    creation_time: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    message: Mapped['Message'] = relationship(back_populates='attachments')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'message_id': self.message_id,
            'filename': self.filename,
            'attachment_type': self.attachment_type,
            'creation_time': self.creation_time.isoformat()
            # content_base64 is not typically returned in list views for brevity
        }


@dataclass
class Chat(db.Model):
    __tablename__ = 'chats'
    
    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    creation_time: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    modification_time: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), index=True)
    head: Mapped[str] = mapped_column(db.String, nullable=True, default=None)
    messages: Mapped[List[Message]] = relationship(
        'Message',
        backref='chat',
        lazy='joined',
        cascade="all, delete-orphan"
    )
    cards: Mapped[List[Card]] = relationship(
        'Card',
        secondary='card_chat_association',
        back_populates='chats',
        lazy='select'
    )

    # Methods add_message, remove_message_by_id, get_message_by_id, edit_message_by_id,
    # get_messages_dict_list, get_linear_chat_from_message_id, to_dict, save_chat,
    # get_chat_by_id, get_chat_list, create_new_chat, get_or_create_latest_chat_for_card
    # moved to DAO/Service layer.