from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class NodeDTO(BaseModel):
    id: Optional[str] = None
    name: str
    node_type: str
    node_subtype: Optional[str] = None
    on: bool
    interface: Dict[str, Union[str, Dict]]
    code: str
    handler: Optional[str] = None
    static_input: Dict[str, Any]
    workflow_id: str

class NodeUpdateDTO(BaseModel):
    name: Optional[str] = None
    node_type: Optional[str] = None
    node_subtype: Optional[str] = None
    on: Optional[bool] = None
    interface: Optional[Dict[str, Union[str, Dict]]] = None
    code: Optional[str] = None
    handler: Optional[str] = None
    static_input: Optional[Dict[str, Any]] = None

class LinkDTO(BaseModel):
    source: str
    target: str

class WorkflowCoreDTO(BaseModel):
    id: str
    name: str

class WorkflowDetailDTO(WorkflowCoreDTO):
    graph: Dict[str, Any]
    nodes: Dict[str, NodeDTO]
    links: List[LinkDTO]

class WorkflowCreateDTO(BaseModel):
    name: str
    graph: Dict[str, Any] = Field(default_factory=dict)
    
class WorkflowUpdateDTO(BaseModel):
    name: Optional[str] = None
    graph: Optional[Dict[str, Any]] = None

class WorkflowSaveDTO(BaseModel):
    name: Optional[str] = None
    graph: Optional[Dict[str, Any]] = None
    nodes: Optional[Dict[str, NodeDTO]] = None
    links: Optional[List[LinkDTO]] = None
    id: Optional[str] = None