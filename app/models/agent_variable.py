
from uuid import uuid4
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

class AgentVariable(db.Model):
    __tablename__ = 'agent_variables'

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(db.String, db.ForeignKey('agents.id'), nullable=False)
    name: Mapped[str] = mapped_column(db.String, nullable=False)
    value: Mapped[dict] = mapped_column(db.JSON, nullable=False)

    agent = relationship('Agent', back_populates='variables')