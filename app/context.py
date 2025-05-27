import logging
from dataclasses import dataclass, field
from app.scheduler import CyclicTaskManager
from app.macros import MacroProcessor, macroProcessor
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from app.runtime_services.agent_service import AgentService
    from app.runtime_services.workflow_service import WorkflowService
    from app.runtime_services.tool_service import ToolService
    from app.models.utils.message_broker import MessageBroker

@dataclass
class Context:
    cyclic_task_manager: CyclicTaskManager = field(default_factory=CyclicTaskManager)
    message_broker: 'MessageBroker' = None
    agents: Dict = field(default_factory=dict)
    chat_id: str = None
    card_id: str = None
    card_version: str = None
    agent_service: 'AgentService' = None
    workflow_service: 'WorkflowService' = None
    tool_service: 'ToolService' = None
    macro_processor: MacroProcessor = macroProcessor
    
    log_level: int = logging.INFO
    
context = Context()
