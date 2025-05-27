from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union, Callable
from uuid import uuid4
from sqlalchemy.orm import Mapped, mapped_column, relationship, reconstructor
from app.extensions import db
from app.events import TriggerType
from app.context import context
from app.utils.utils import create_logger
from .utils import ACLMessage
from .context_block import ContextBlock, ContextPositionType
from .context_manager import ContextManager, ContextItem, merge_context_items_by_role, resolve_context_items_content
from app.helpers.agent_helpers import update_agent_variable
from app.api.chat_completions_api import OpenAICompletions
from app.helpers.chat_helpers import (
    get_chat_history, add_one_message,
    remove_last_message, remove_message_by_id, get_last_message,
    get_message_by_id, edit_message_by_id, get_message_var,
    set_message_var, remove_message_var
)
from app.node_default_handlers import (
    ResourceNode, ActionNode, GeneratorNode,
    get_chat_history_node, squash_roles_chat_history_node, convert_to_openai_chat_history_node,
    openai_chat_completion_generator_node, execute_tool_call_node,
    append_tool_results_to_history_node, handle_send_acl_message, handle_extract_acl_content,
    filter_by_tool_use_node
)
from app.node_default_handlers.tool_management import (
    register_standard_tool_node, delete_standard_tool_node, get_tool_schemas_node,
    register_custom_tool_node, delete_custom_tool_node  # Added new handlers
)

wf_log = create_logger(__name__, entity_name='WORKFLOW_MODEL', level=context.log_level)

node_types: List[str] = ['trigger', 'resource', 'action', 'generator', 'custom']

node_subtypes: Dict[str, List[str]] = {
    'trigger': [
        TriggerType.INIT,
        TriggerType.STOP,
        TriggerType.CYCLIC,
        TriggerType.CHAT_START,
        TriggerType.CHAT_MESSAGE_RECEIVED,
        TriggerType.BROADCAST
    ],
    'resource': [
        ResourceNode.CHAT_HISTORY,
        ResourceNode.GET_TOOL_SCHEMAS,
    ],
    'action': [
        ActionNode.SQUASH_HISTORY,
        ActionNode.CONVERT_TO_OPENAI_HISTORY,
        ActionNode.EXECUTE_TOOL_CALL,
        ActionNode.REGISTER_STANDARD_TOOL,
        ActionNode.DELETE_STANDARD_TOOL,
        ActionNode.SEND_ACL_MESSAGE,
        ActionNode.APPEND_TOOL_RESULTS_TO_HISTORY,
        ActionNode.EXTRACT_ACL_CONTENT,
        ActionNode.FILTER_BY_TOOL_USE,
        ActionNode.REGISTER_CUSTOM_TOOL,  # Added new subtype
        ActionNode.DELETE_CUSTOM_TOOL,    # Added new subtype
    ],
    'generator': [
        GeneratorNode.OPENAI_CHAT_COMPLETION_STREAM,
    ],
    'custom': [
        'python',
        #'lua' # temporarily unavailable
    ]
}

PYTHON_NODE_GLOBALS: Dict[str, Any] = {
    'context': context,
    'ACLMessage': ACLMessage,
    'ContextBlock': ContextBlock,
    'ContextPositionType': ContextPositionType,
    'ContextManager': ContextManager,
    'ContextItem': ContextItem,
    'OpenAICompletions': OpenAICompletions,
    'update_agent_variable': update_agent_variable,
    'get_chat_history': get_chat_history,
    'add_one_message': add_one_message,
    'remove_last_message': remove_last_message,
    'remove_message_by_id': remove_message_by_id,
    'get_last_message': get_last_message,
    'get_message_by_id': get_message_by_id,
    'edit_message_by_id': edit_message_by_id,
    'get_message_var': get_message_var,
    'set_message_var': set_message_var,
    'remove_message_var': remove_message_var,
    'merge_context_items_by_role': merge_context_items_by_role,
    'resolve_context_items_content': resolve_context_items_content,
}

NODE_DEFAULT_HANDLERS: Dict[str, Callable] = {
    ResourceNode.CHAT_HISTORY: get_chat_history_node,
    ActionNode.SQUASH_HISTORY: squash_roles_chat_history_node,
    ActionNode.EXECUTE_TOOL_CALL: execute_tool_call_node,
    ActionNode.CONVERT_TO_OPENAI_HISTORY: convert_to_openai_chat_history_node,
    GeneratorNode.OPENAI_CHAT_COMPLETION_STREAM: openai_chat_completion_generator_node,
    ActionNode.REGISTER_STANDARD_TOOL: register_standard_tool_node,
    ActionNode.DELETE_STANDARD_TOOL: delete_standard_tool_node,
    ResourceNode.GET_TOOL_SCHEMAS: get_tool_schemas_node,
    ActionNode.SEND_ACL_MESSAGE: handle_send_acl_message,
    ActionNode.APPEND_TOOL_RESULTS_TO_HISTORY: append_tool_results_to_history_node,
    ActionNode.EXTRACT_ACL_CONTENT: handle_extract_acl_content,
    ActionNode.FILTER_BY_TOOL_USE: filter_by_tool_use_node,
    ActionNode.REGISTER_CUSTOM_TOOL: register_custom_tool_node,  # Added new handler mapping
    ActionNode.DELETE_CUSTOM_TOOL: delete_custom_tool_node,    # Added new handler mapping
}

@dataclass
class Node(db.Model):
    __tablename__ = 'nodes'

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(db.String, nullable=False)
    node_type: Mapped[str] = mapped_column(db.String, nullable=False)
    node_subtype: Mapped[str] = mapped_column(db.String, default='')
    on: Mapped[bool] = mapped_column(db.Boolean, default=True)
    interface: Mapped[Dict[str, Union[str, Dict]]] = mapped_column(db.JSON, default=dict)
    code: Mapped[str] = mapped_column(db.Text, default='')
    handler: Mapped[Optional[str]] = mapped_column(db.Text, default=None)
    workflow_id: Mapped[str] = mapped_column(db.String, db.ForeignKey('workflows.id'), nullable=False)
    static_input: Mapped[Dict[str, str]] = mapped_column(db.JSON, default=dict)

    handler_func: Optional[Callable] = field(default=None, init=False, repr=False, compare=False)

    def _get_handler_func(self):
        """Sets the handler_func based on the handler string."""
        if self.handler and isinstance(self.handler, str):
            self.handler_func = NODE_DEFAULT_HANDLERS.get(self.handler)
        else:
            self.handler_func = None

    @reconstructor
    def init_on_load(self):
        """Initialize non-persistent fields after object construction or loading."""
        self._get_handler_func()

    @staticmethod
    def get_nodes_types() -> List[str]:
        return node_types

    @staticmethod
    def get_nodes_subtypes_by_type(node_type: str) -> List[str]:
        if node_type in node_subtypes:
            return node_subtypes[node_type]
        else:
            return []


@dataclass
class Link(db.Model):
    __tablename__ = 'links'

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid4()))
    source: Mapped[str] = mapped_column(db.String, db.ForeignKey('nodes.id'), nullable=False)
    target: Mapped[str] = mapped_column(db.String, db.ForeignKey('nodes.id'), nullable=False)
    workflow_id: Mapped[str] = mapped_column(db.String, db.ForeignKey('workflows.id'), nullable=False)


@dataclass
class WorkflowTempVar(db.Model):
    __tablename__ = 'workflow_temp_vars'

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(db.String, db.ForeignKey('workflows.id'), nullable=False, index=True)
    key: Mapped[str] = mapped_column(db.String, nullable=False, index=True)
    value: Mapped[Any] = mapped_column(db.PickleType, nullable=True)

    __table_args__ = (db.UniqueConstraint('workflow_id', 'key', name='_workflow_key_uc'),)

    def __repr__(self):
        value_repr = repr(self.value)
        if len(value_repr) > 50:
            value_repr = value_repr[:47] + '...'
        return f"<WorkflowTempVar(workflow_id='{self.workflow_id}', key='{self.key}', value={value_repr})>"


@dataclass
class Workflow(db.Model):
    __tablename__ = 'workflows'

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(db.String, nullable=False)
    graph: Mapped[Dict[str, Any]] = mapped_column(db.JSON, default=dict)

    nodes: Mapped[List['Node']] = relationship('Node', backref='workflow', lazy='select', cascade="all, delete-orphan")
    links: Mapped[List['Link']] = relationship('Link', backref='workflow', lazy='select', cascade="all, delete-orphan")
    temp_vars: Mapped[List['WorkflowTempVar']] = relationship('WorkflowTempVar', backref='workflow', lazy='dynamic', cascade="all, delete-orphan")