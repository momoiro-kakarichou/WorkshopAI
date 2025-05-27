from dataclasses import dataclass
from typing import List
from uuid import uuid4
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db
from .agent_variable import AgentVariable

@dataclass
class Agent(db.Model):
    """Represents an Agent entity in the database."""
    __tablename__ = 'agents'

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(db.String, default='')
    version: Mapped[str] = mapped_column(db.String, default='1.0.0')
    description: Mapped[str] = mapped_column(db.String, default='')
    workflow_id: Mapped[str] = mapped_column(db.String, db.ForeignKey('workflows.id'), default='')

    variables: Mapped[List['AgentVariable']] = relationship(
        'AgentVariable',
        back_populates='agent',
        cascade='all, delete-orphan',
        lazy='select'
    )
    cards = relationship(
        'Card',
        secondary='agent_card_association',
        back_populates='agents',
        lazy='select'
    )

    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', version='{self.version}')>"