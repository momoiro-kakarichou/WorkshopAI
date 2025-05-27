from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class MessageVarDTO(BaseModel):
    key: str
    value: Optional[Any]

class AttachmentDTO(BaseModel):
    id: str
    message_id: str
    filename: str
    attachment_type: Optional[str] = None
    creation_time: str
    content_base64: Optional[str] = None # Optional, as it might not always be sent

class MessageDTO(BaseModel):
    id: str
    chat_id: str
    parent_id: Optional[str] = None
    depth: int
    role: str
    creation_time: str
    modification_time: str
    card_id: Optional[str] = None
    card_version: Optional[str] = None
    content: str
    card_name: Optional[str] = None
    card_avatar_uri: Optional[str] = None
    vars: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[AttachmentDTO] = Field(default_factory=list)

class ChatDTO(BaseModel):
    id: str
    name: str
    messages: List[MessageDTO] = Field(default_factory=list)