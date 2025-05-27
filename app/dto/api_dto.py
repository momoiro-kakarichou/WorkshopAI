from pydantic import BaseModel
from typing import Optional, List

class ApiDTO(BaseModel):
    """Data Transfer Object for API configurations using Pydantic."""
    name: str
    api_type: str
    source: str
    api_url: str
    api_key: str
    model: str
    id: Optional[str] = None
    tags: List[str] = ['default']

    class Config:
        from_attributes = True