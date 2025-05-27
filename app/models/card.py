import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import ForeignKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
# Removed unused imports like os, json, shutil, PIL, BytesIO, db utils, constants

# CardAssetType: TypeAlias = Literal[
#     'context', 'image', 'video', 'audio', 'document', 'other'
# ]

# CommonTag: TypeAlias = Literal[
#     'card_avatar', 'user_avatar', 'background'
# ]

agent_card_association = db.Table(
    'agent_card_association',
    db.Column('agent_id', db.String, db.ForeignKey('agents.id'), primary_key=True),
    db.Column('card_id', db.String, db.ForeignKey('cards.id'), primary_key=True)
)

card_chat_association = db.Table(
    'card_chat_association',
    db.Column('card_id', db.String, db.ForeignKey('cards.id'), primary_key=True),
    db.Column('chat_id', db.String, db.ForeignKey('chats.id'), primary_key=True)
)

class CardContextAsset(db.Model):
    __tablename__ = 'card_context_assets'
    
    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(db.String(50), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(db.String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False, index=True)
    ext: Mapped[str] = mapped_column(db.String(10), nullable=False)
    data: Mapped[dict] = mapped_column(db.JSON, nullable=False)
    card_id: Mapped[str] = mapped_column(db.String, nullable=False)
    card_version: Mapped[str] = mapped_column(db.String, nullable=False)
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['card_id', 'card_version'], 
            ['cards.id', 'cards.version'],
            name='card_context_asset_fk', 
            ondelete='CASCADE'
        ),
        Index('idx_card_context_asset_card_id_version', 'card_id', 'card_version'),
    )

    # __init__ is implicitly handled by SQLAlchemy/Mapped
    # Removed methods: edit_from_dict, to_dict, validate_data, get_context_asset_by_id
    # These are now handled by DAO/Service/DTO layers


class CardFileAsset(db.Model):
    __tablename__ = 'card_file_assets'
    
    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(db.String(50), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(db.String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False, index=True)
    ext: Mapped[str] = mapped_column(db.String(10), nullable=False)
    uri: Mapped[str] = mapped_column(db.String(255), nullable=False)
    card_id: Mapped[str] = mapped_column(db.String, nullable=False)
    card_version: Mapped[str] = mapped_column(db.String, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ['card_id', 'card_version'], 
            ['cards.id', 'cards.version'],
            name='card_file_asset_fk',  
            ondelete='CASCADE'
        ),
        Index('idx_card_file_asset_card_id_version', 'card_id', 'card_version'),
    )

    # __init__ is implicitly handled by SQLAlchemy/Mapped
    # Removed methods: edit_from_dict, to_dict, get_file_path, get_file_url, get_file, validate_data, get_file_asset_by_id
    # These are now handled by DAO/Service/DTO layers


class Card(db.Model):
    __tablename__ = 'cards'
    
    id: Mapped[str] = mapped_column(db.String, primary_key=True)
    version: Mapped[str] = mapped_column(db.String(20), primary_key=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    creator: Mapped[str] = mapped_column(db.String(100), nullable=False)
    creator_note: Mapped[str] = mapped_column(db.Text, nullable=True)
    tags: Mapped[list] = mapped_column(db.JSON, nullable=False, default=[])
    creation_date: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    modification_date: Mapped[datetime] = mapped_column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc), index=True)
    context_assets: Mapped[List[CardContextAsset]] = relationship(
        'CardContextAsset', 
        backref='card', 
        lazy=True,
        cascade="all, delete-orphan"
    )
    file_assets: Mapped[List[CardFileAsset]] = relationship(
        'CardFileAsset', 
        backref='card', 
        lazy=True,
        cascade="all, delete-orphan"
    )
    agents = relationship(
        'Agent',
        secondary='agent_card_association',
        back_populates='cards'
    )
    chats = relationship(
        'Chat',
        secondary='card_chat_association',
        back_populates='cards'
    )

    # __init__ is implicitly handled by SQLAlchemy/Mapped
    # Removed instance methods: edit_from_dict, to_dict, save_card, attach_agent, detach_agent,
    # get_card_avatar, change_card_avatar, create_context_asset, create_file_asset,
    # edit_context_asset, delete_context_asset, edit_file_asset, delete_file_asset, fork_card
    # Removed static methods: get_by_primary_key, get_by_id, get_card_ids_list, get_all_cards_list,
    # get_by_chat_id, get_by_name, filter_by_name_part, delete_card_by_primary_key,
    # delete_cards_by_id, delete_assets_if_no_cards, get_default_avatar_url
    # These are now handled by DAO/Service layers