from enum import Enum
from typing import Callable, Dict, List, Any


class DataEventType(Enum):
    """
    Enumeration for different types of events.
    """
    MESSAGE_START = 'message_start'
    MESSAGE_END = 'message_end'
    MESSAGE_DELTA = 'message_delta'
    MESSAGE_COMPLETE = 'message_complete'
    STREAMED_MESSAGE_COMPLETE = 'streamed_message_complete'
    TOOL_CALL_DELTA = 'tool_call_delta'
    TOOL_CALL_COMPLETE = 'tool_call_complete'
    METADATA_RECEIVED = 'metadata_received'
    ERROR = 'error'
    INFO = 'info'


class DataEvent:
    """
    Class representing an event with type and data.
    Allows registration and handling of event-specific handlers.
    """
    _handlers: Dict[DataEventType, List[Callable[[Any], None]]] = {}

    def __init__(self, type: DataEventType, data: Any, quiet: bool = False):
        """
        Initialize a MessageEvent.

        Args:
            type (EventType): The type of the event.
            data (Any): The data associated with the event.
            quiet (bool): Quiet mode (event will not execute handlers)
        """
        self.type = type
        self.data = data
        self.quiet = quiet

    @classmethod
    def register_handler(cls, event_type: DataEventType, handler: Callable[[Any], None]):
        """
        Register a handler for a specific event type.

        Args:
            event_type (EventType): The type of event to register the handler for.
            handler (Callable[[Any], None]): The handler function to be called when the event occurs.
        """
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)

    def handle(self):
        """
        Call all registered handlers for this event's type.
        """
        if not self.quiet and self.type in self._handlers:
            for handler in self._handlers[self.type]:
                handler(self.data)
                

class SocketIOEventType:
    # receivable events
    CONNECT = 'connect'
    PING = 'ping'
    ERROR = 'error'
    
    API_REQUEST = 'api_request'
    API_LIST_REQUEST = 'api_list_request'
    API_SOURCE_REQUEST = 'api_source_request'
    API_MODEL_REQUEST = 'api_model_request'
    API_SAVE_REQUEST = 'api_save_request'
    API_DELETE_REQUEST = 'api_delete_request'
    API_FETCH_EXTERNAL_MODELS_REQUEST = 'api_fetch_external_models_request'
    
    AGENT_REQUEST = 'agent_request'
    AGENT_LIST_REQUEST = 'agent_list_request'
    AGENT_START_REQUEST = 'agent_start_request'
    AGENT_STOP_REQUEST = 'agent_stop_request'
    AGENT_SAVE_REQUEST = 'agent_save_request'
    AGENT_DELETE_REQUEST = 'agent_delete_request'
    AGENT_NEW_VAR_REQUEST = 'agent_new_var_request'
    AGENT_IMPORT_VARS_REQUEST = 'agent_import_vars_request'
    AGENT_EDIT_VAR_REQUEST = 'agent_edit_var_request'
    AGENT_DELETE_VAR_REQUEST = 'agent_delete_var_request'
    
    MESSAGE_TO_INTERFACE_AGENT = 'message_to_interface_agent'
    
    WORKFLOW_REQUEST = 'workflow_request'
    WORKFLOW_LIST_REQUEST = 'workflow_list_request'
    WORKFLOW_SAVE_REQUEST = 'workflow_save_request'
    WORKFLOW_DELETE_REQUEST = 'workflow_delete_request'
    
    NODE_GET_TYPES_REQUEST = 'node_get_types_request'
    NODE_GET_SUBTYPES_REQUEST = 'node_get_subtypes_request'
    NODE_CONTENT_REQUEST = 'node_request'
    NODE_SAVE_REQUEST = 'node_save_request'
    NODE_DELETE_REQUEST = 'node_delete_request'
    NODE_GET_DYNAMIC_OPTIONS_REQUEST = 'node_get_dynamic_options_request'
    
    LINK_CREATE_REQUEST = 'link_create_request'
    LINK_DELETE_REQUEST = 'link_delete_request'
    
    CARD_REQUEST = 'card_request'
    CARD_LIST_REQUEST = 'card_list_request'
    CARD_SAVE_REQUEST = 'card_save_request'
    CARD_DELETE_REQUEST = 'card_delete_request'
    
    CHAT_REQUEST = 'chat_request'
    NEW_CHAT_REQUEST = 'new_chat_request'
    CHAT_LIST_REQUEST = 'chat_list_request'
    
    USER_MESSAGE_SEND = 'user_message_send'
    SWIPE_REQUEST = 'swipe_request'
    GET_MESSAGE_REQUEST = 'get_message_request'
    EDIT_MESSAGE_REQUEST = 'edit_message_request'
    REMOVE_MESSAGE_REQUEST = 'remove_message_request'
    GET_OR_CREATE_LATEST_CHAT_REQUEST = 'get_or_create_latest_chat_request'
    ADD_ATTACHMENT_REQUEST = 'add_attachment_request'
    REMOVE_ATTACHMENT_REQUEST = 'remove_attachment_request'
    
    SHOW_MODAL_REQUEST = 'show_modal_request'
    SHOW_TOASTR_REQUEST = 'show_toastr_request' # Added for toastr
 
 
    # sendable events
    PONG = 'pong'
    
    API = 'api'
    API_LIST = 'api_list'
    API_SOURCE = 'api_source'
    API_MODEL = 'api_model'
    API_SAVE = 'api_save'
    API_DELETE = 'api_delete'
    API_FETCH_EXTERNAL_MODELS_RESPONSE = 'api_fetch_external_models_response'
    
    AGENT = 'agent'
    AGENT_LIST = 'agent_list'
    AGENT_START = 'agent_start'
    AGENT_SAVE = 'agent_save'
    AGENT_STOP = 'agent_stop'
    AGENT_DELETE = 'agent_delete'
    AGENT_NEW_VAR = 'agent_new_var'
    AGENT_IMPORT_VARS = 'agent_import_vars'
    AGENT_EDIT_VAR = 'agent_edit_var'
    AGENT_DELETE_VAR = 'agent_delete_var'
    
    MESSAGE_FROM_INTERFACE_AGENT = 'message_from_interface_agent'
    
    WORKFLOW = 'workflow'
    WORKFLOW_LIST = 'workflow_list'
    WORKFLOW_SAVE= 'workflow_save'
    WORKFLOW_DELETE = 'workflow_delete'
    
    NODE_GET_TYPES = 'node_get_types'
    NODE_GET_SUBTYPES = 'node_get_subtypes'
    NODE_CONTENT = 'node'
    NODE_SAVE = 'node_save'
    NODE_DELETE = 'node_delete'
    NODE_GET_DYNAMIC_OPTIONS = 'node_get_dynamic_options'
    
    LINK_CREATE = 'link_create'
    LINK_DELETE = 'link_delete'
    
    CARD = 'card'
    CARD_LIST = 'card_list'
    CARD_SAVE = 'card_save'
    CARD_DELETE = 'card_delete'
    
    CHAT = 'chat'
    NEW_CHAT = 'new_chat'
    CHAT_LIST = 'chat_list'
    GET_OR_CREATE_LATEST_CHAT = 'get_or_create_latest_chat'

    MESSAGE_START = 'message_start'
    MESSAGE_END = 'message_end'
    MESSAGE_DELTA = 'message_delta'
    MESSAGE_RECEIVED = 'message_received'
    STREAMED_MESSAGE_RECEIVED = 'streamed_message_received'
    TOOL_CALL_CHUNK = 'tool_call_chunk'
    TOOL_CALL = 'tool_call'
    METADATA = 'metadata'
    
    SWIPE = 'swipe'
    GET_MESSAGE = 'get_message'
    EDIT_MESSAGE = 'edit_message'
    REMOVE_MESSAGE = 'remove_message'
    ADD_ATTACHMENT_RESPONSE = 'add_attachment_response'
    REMOVE_ATTACHMENT_RESPONSE = 'remove_attachment_response'
    
    SHOW_MODAL = 'show_modal'
    SHOW_TOASTR = 'show_toastr' # Added for toastr
    
class TriggerType:
    INIT = '/agent/init'
    STOP = '/agent/stop'
    CYCLIC = '/agent/cyclic'
    CHAT_START = '/system/chat/start'
    CHAT_MESSAGE_RECEIVED = '/system/chat/new_message'
    BROADCAST = '/broadcast'