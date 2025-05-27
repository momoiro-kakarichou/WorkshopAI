from .agent_service import AgentService
from .workflow_service import WorkflowService
from .tool_service import ToolService

def init_app(app, context):
    agent_service = AgentService()
    agent_service.init_app(app, context.message_broker)
    context.agent_service = agent_service
    
    workflow_service = WorkflowService()
    context.workflow_service = workflow_service
    
    tool_service = ToolService()
    context.tool_service = tool_service