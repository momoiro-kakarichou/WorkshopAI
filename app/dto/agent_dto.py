from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class AgentVariableDTO(BaseModel):
    name: str
    value: Any

class AgentCoreDTO(BaseModel):
    id: str
    name: str
    version: str
    description: str
    workflow_id: str
    vars: Dict[str, Any] = Field(default_factory=dict)

class AgentListDTO(BaseModel):
    id: str
    name: str

class AgentDetailDTO(AgentCoreDTO):
    versions_list: List[str] = Field(default_factory=list)

class AgentRuntimeInfoDTO(BaseModel):
    is_started: bool

class AgentFullDTO(AgentDetailDTO, AgentRuntimeInfoDTO):
    pass

class AgentCreateDTO(BaseModel):
    name: str
    workflow_id: str
    description: Optional[str] = None
    version: str = '1.0.0' # Default version
    vars: Optional[Dict[str, Any]] = None

class AgentUpdateDTO(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    workflow_id: Optional[str] = None
    vars: Optional[Dict[str, Any]] = None # For replacing all vars