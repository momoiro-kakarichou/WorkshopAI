from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
import uuid

# --- Asset DTOs ---

class CardContextAssetDTO(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = Field(..., max_length=50)
    tag: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    ext: str = Field(..., max_length=10)
    data: Dict[str, Any]
    card_id: str
    card_version: str

    model_config = {"from_attributes": True}

class CardFileAssetDTO(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = Field(..., max_length=50)
    tag: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    ext: str = Field(..., max_length=10)
    uri: str = Field(..., max_length=255)
    url: Optional[str] = None
    card_id: str
    card_version: str

    model_config = {"from_attributes": True}

# --- Card DTO ---

class CardBasicDTO(BaseModel):
    id: str
    version: str
    name: str
    avatar_uri: Optional[str] = None

    model_config = {"from_attributes": True}

class CardDTO(BaseModel):
    id: str
    version: str
    name: str = Field(..., max_length=100)
    creator: str = Field(default="", max_length=100)
    creator_note: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    creation_date: datetime
    modification_date: datetime
    context_assets: List[CardContextAssetDTO] = Field(default_factory=list)
    file_assets: List[CardFileAssetDTO] = Field(default_factory=list)
    agents: List[str] = Field(default_factory=list)
    chats: List[str] = Field(default_factory=list)

    @field_validator('creation_date', 'modification_date', mode='before')
    @classmethod
    def ensure_datetime(cls, v: Any) -> datetime:
        if isinstance(v, str):
            try:
                # Handle 'Z' for UTC explicitly
                if v.endswith('Z'):
                    v = v[:-1] + '+00:00'
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError(f"Invalid datetime format: {v}")
        elif isinstance(v, datetime):
            return v
        raise TypeError("Input must be a string or datetime object")

    model_config = {"from_attributes": True}

class CardCreateDTO(BaseModel):
    name: str = Field(..., max_length=100)
    creator: str = Field(default="", max_length=100)
    creator_note: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    id: Optional[str] = None
    version: str = Field(default="1.0.0", max_length=20)

class CardUpdateDTO(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    creator: Optional[str] = Field(None, max_length=100)
    creator_note: Optional[str] = None
    tags: Optional[List[str]] = None

    @model_validator(mode='before')
    @classmethod
    def check_at_least_one_value(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data:
                 raise ValueError("At least one field must be provided for update")
            if all(v is None for v in data.values()):
                 raise ValueError("At least one field must be provided for update")
        return data

class CardAssetCreateUpdateDTO(BaseModel):
    type: str = Field(..., max_length=50)
    tag: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    ext: str = Field(..., max_length=10)
    data: Optional[Dict[str, Any]] = None
    uri: Optional[str] = Field(None, max_length=255)

    @model_validator(mode='after')
    def check_uri_or_data(self) -> 'CardAssetCreateUpdateDTO':
        if self.data is None and self.uri is None:
            raise ValueError("Either 'data' (for context asset) or 'uri' (for file asset) must be provided.")
        if self.data is not None and self.uri is not None:
            raise ValueError("Provide either 'data' (for context asset) or 'uri' (for file asset), not both.")
        return self