class ResourceNode:
    CHAT_HISTORY = 'chat_history'
    GET_TOOL_SCHEMAS = "get_tool_schemas"
    
class ActionNode:
    SQUASH_HISTORY = 'squash_history'
    CONVERT_TO_OPENAI_HISTORY = 'convert_to_openai_history'
    EXECUTE_TOOL_CALL = 'execute_tool_call'
    REGISTER_STANDARD_TOOL = "register_standard_tool"
    DELETE_STANDARD_TOOL = "delete_standard_tool"
    SEND_ACL_MESSAGE = "send_acl_message"
    APPEND_TOOL_RESULTS_TO_HISTORY = 'append_tool_results_to_history'
    EXTRACT_ACL_CONTENT = "extract_acl_content"
    FILTER_BY_TOOL_USE = 'filter_by_tool_use'
    REGISTER_CUSTOM_TOOL = "register_custom_tool"
    DELETE_CUSTOM_TOOL = "delete_custom_tool"
    
class GeneratorNode:
    OPENAI_GENERATOR = 'openai_generator'
    OPENAI_CHAT_COMPLETION_STREAM = 'openai_chat_completion_stream'

