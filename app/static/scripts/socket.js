export var socket = io({ pingTimeout: 10000 });

export function waitForEvent(eventName) {
    return new Promise((resolve) => {
        socket.once(eventName, resolve);
    });
}

export const ChatEvent = {
    CHAT: 'chat',
    CHAT_REQUEST: 'chat_request',
    GET_OR_CREATE_LATEST_CHAT: 'get_or_create_latest_chat',
    GET_OR_CREATE_LATEST_CHAT_REQUEST: 'get_or_create_latest_chat_request'
};

export const MessageEvent = {
    MESSAGE_START: 'message_start',
    MESSAGE_DELTA: 'message_delta',
    MESSAGE_END: 'message_end',
    MESSAGE_RECEIVED: 'message_received',
    STREAMED_MESSAGE_RECEIVED: 'streamed_message_received',
    USER_MESSAGE_SEND: 'user_message_send',
    GET_MESSAGE_REQUEST: 'get_message_request',
    GET_MESSAGE: 'get_message',
    EDIT_MESSAGE_REQUEST: 'edit_message_request',
    EDIT_MESSAGE: 'edit_message',
    REMOVE_MESSAGE_REQUEST: 'remove_message_request',
    REMOVE_MESSAGE: 'remove_message'
};

export const WorkflowEvent = {
    WORKFLOW_REQUEST: 'workflow_request',
    WORKFLOW_LIST_REQUEST: 'workflow_list_request',
    WORKFLOW_SAVE_REQUEST: 'workflow_save_request',
    WORKFLOW_DELETE_REQUEST: 'workflow_delete_request',
    NODE_GET_TYPES_REQUEST: 'node_get_types_request',
    NODE_GET_SUBTYPES_REQUEST: 'node_get_subtypes_request',
    NODE_CONTENT_REQUEST: 'node_request',
    NODE_SAVE_REQUEST: 'node_save_request',
    NODE_DELETE_REQUEST: 'node_delete_request',
    NODE_GET_DYNAMIC_OPTIONS_REQUEST: 'node_get_dynamic_options_request',
    LINK_CREATE_REQUEST: 'link_create_request',
    LINK_DELETE_REQUEST:'link_delete_request',
    WORKFLOW: 'workflow',
    WORKFLOW_LIST: 'workflow_list',
    WORKFLOW_SAVE: 'workflow_save',
    WORKFLOW_DELETE: 'workflow_delete',
    NODE_GET_TYPES: 'node_get_types',
    NODE_GET_SUBTYPES: 'node_get_subtypes',
    NODE_CONTENT: 'node',
    NODE_SAVE: 'node_save',
    NODE_DELETE: 'node_delete',
    NODE_GET_DYNAMIC_OPTIONS: 'node_get_dynamic_options',
    LINK_CREATE: 'link_create',
    LINK_DELETE: 'link_delete'    
};

export const AgentEvent = {
    AGENT_REQUEST: 'agent_request',
    AGENT_LIST_REQUEST: 'agent_list_request',
    AGENT_START_REQUEST: 'agent_start_request',
    AGENT_STOP_REQUEST: 'agent_stop_request',
    AGENT_SAVE_REQUEST: 'agent_save_request',
    AGENT_DELETE_REQUEST: 'agent_delete_request',
    AGENT_NEW_VAR_REQUEST: 'agent_new_var_request',
    AGENT_IMPORT_VARS_REQUEST: 'agent_import_vars_request',
    AGENT_DELETE_VAR_REQUEST: 'agent_delete_var_request',
    AGENT: 'agent',
    AGENT_LIST: 'agent_list',
    AGENT_START: 'agent_start',
    AGENT_STOP: 'agent_stop',
    AGENT_SAVE: 'agent_save',
    AGENT_DELETE: 'agent_delete',
    AGENT_NEW_VAR: 'agent_new_var',
    AGENT_IMPORT_VARS: 'agent_import_vars',
    AGENT_DELETE_VAR: 'agent_delete_var',
};

export const CardEvent = {
    CARD_REQUEST: 'card_request',
    CARD_SAVE_REQUEST: 'card_save_request',
    CARD_DELETE_REQUEST: 'card_delete_request',
    CARD_LIST_REQUEST: 'card_list_request',
    CARD: 'card',
    CARD_SAVE: 'card_save',
    CARD_DELETE: 'card_delete',
    CARD_LIST: 'card_list'
};

export const InterfaceEvent = {
    SHOW_MODAL: 'show_modal',
    SHOW_TOASTR: 'show_toastr'
}