import json
from typing import Callable, Dict, Any
from app.context import context
from app.utils.utils import create_logger

tool_mgmt_log = create_logger(__name__, entity_name='TOOL_MGMT_NODE', level=context.log_level)

def _compile_custom_tool_function(py_code_str: str, expected_func_name: str) -> Callable:
    """
    Compiles a Python code string into a callable function.
    The Python code string is expected to define a function with the name `expected_func_name`.
    """
    local_scope: Dict[str, Any] = {}
    # Using a less restrictive global scope by copying the module's globals.
    # This allows broader import capabilities (project modules, third-party libs)
    # but has significant security implications. User is aware and has requested this.
    permissive_global_scope = globals().copy()
    
    if not isinstance(py_code_str, str):
        raise TypeError("Python code for tool function must be a string.")

    try:
        compiled_code = compile(py_code_str, f"<custom_tool_{expected_func_name}>", 'exec')
        exec(compiled_code, permissive_global_scope, local_scope)
    except SyntaxError as se:
        tool_mgmt_log.error(f"Syntax error compiling custom tool '{expected_func_name}': {se}")
        raise ValueError(f"Syntax error in tool function code: {se}")
    except Exception as e:
        tool_mgmt_log.error(f"Error compiling/executing custom tool '{expected_func_name}': {e}")
        raise ValueError(f"Error during tool function compilation: {e}")

    if expected_func_name not in local_scope or not callable(local_scope[expected_func_name]):
        found_func = None
        found_name = None
        for name, item in local_scope.items():
            if callable(item) and not name.startswith("__"):
                if found_func is None:
                    found_func = item
                    found_name = name
                else:
                    tool_mgmt_log.error(
                        f"Multiple functions found in custom tool code for '{expected_func_name}', "
                        f"but none match the expected name. Found: {[n for n,i in local_scope.items() if callable(i) and not n.startswith('__')]}"
                    )
                    raise ValueError(
                        f"Multiple functions defined in the code for tool '{expected_func_name}', "
                        f"but none match the expected name. Please define one function named '{expected_func_name}'."
                    )
        if found_func and found_name:
            tool_mgmt_log.warning(
                f"Custom tool function '{expected_func_name}' not found directly. "
                f"Using the discovered callable '{found_name}' from the provided code. "
                "It's recommended that the function in your code is named identically to the 'Custom Tool Name'."
            )
            return found_func
        
        raise ValueError(
            f"Could not find a callable function named '{expected_func_name}' in the provided Python code. "
            "Please ensure your Python code defines a function with this exact name."
        )
    
    return local_scope[expected_func_name]


def register_standard_tool_node(
    write_output: Callable,
    static_input: dict,
    node_id: str,
    *args, **kwargs
):
    """Node handler to register a standard tool using ToolService."""
    tool_name = static_input.get('tool_name')
    agent_id = kwargs.get('agent_id')
    output_key = 'registration_result'

    if not agent_id:
        error_msg = f"Node {node_id}: Missing 'agent_id' in node execution context."
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name})
        return

    if not tool_name:
        error_msg = f"Node {node_id}: Missing 'tool_name' in static input for agent '{agent_id}'."
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'agent_id': agent_id})
        return

    try:
        context.tool_service.register_standard_tool(agent_id, tool_name)
        success_msg = f"Standard tool '{tool_name}' registered successfully for agent '{agent_id}'."
        tool_mgmt_log.info(f"Node {node_id}: {success_msg}")
        write_output(output_key, {'success': True, 'message': success_msg, 'tool_name': tool_name, 'agent_id': agent_id})
    except ValueError as ve:
        error_msg = f"Node {node_id}: Value error registering tool '{tool_name}' for agent '{agent_id}': {ve}"
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name, 'agent_id': agent_id})
    except Exception as e:
        error_msg = f"Node {node_id}: Unexpected error registering tool '{tool_name}' for agent '{agent_id}': {e}"
        tool_mgmt_log.exception(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name, 'agent_id': agent_id})


def delete_standard_tool_node(
    write_output: Callable,
    static_input: dict,
    node_id: str,
    *args, **kwargs
):
    """Node handler to delete/deregister a standard tool using ToolService."""
    tool_name = static_input.get('tool_name')
    agent_id = kwargs.get('agent_id')
    output_key = 'deletion_result'

    if not agent_id:
        error_msg = f"Node {node_id}: Missing 'agent_id' in node execution context."
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name})
        return

    if not tool_name:
        error_msg = f"Node {node_id}: Missing 'tool_name' in static input for agent '{agent_id}'."
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'agent_id': agent_id})
        return

    try:
        context.tool_service.delete_tool(agent_id, tool_name)
        success_msg = f"Tool '{tool_name}' deleted successfully for agent '{agent_id}'."
        tool_mgmt_log.info(f"Node {node_id}: {success_msg}")
        write_output(output_key, {'success': True, 'message': success_msg, 'tool_name': tool_name, 'agent_id': agent_id})
    except Exception as e:
        error_msg = f"Node {node_id}: Unexpected error deleting tool '{tool_name}' for agent '{agent_id}': {e}"
        tool_mgmt_log.exception(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name, 'agent_id': agent_id})


def get_tool_schemas_node(
    write_output: Callable,
    static_input: dict,
    node_id: str,
    *args, **kwargs
):
    """Node handler to retrieve currently registered tool schemas for a specific agent."""
    convert_to = static_input.get('convert_to', 'OpenAI')
    agent_id = kwargs.get('agent_id')
    output_key = 'tool_schemas'

    if not agent_id:
        error_msg = f"Node {node_id}: Missing 'agent_id' in node execution context for retrieving tool schemas."
        tool_mgmt_log.error(error_msg)
        write_output(output_key, [])
        return

    try:
        schemas = context.tool_service.get_tool_schemas(agent_id)
        tool_mgmt_log.info(f"Node {node_id}: Retrieved {len(schemas)} tool schemas for agent '{agent_id}'.")

        if convert_to == 'OpenAI':
            processed_schemas = schemas
            output_key = 'openai_tools'
        else:
            tool_mgmt_log.warning(f"Node {node_id}: Unsupported schema conversion format '{convert_to}' for agent '{agent_id}'. Returning raw schemas.")
            processed_schemas = schemas

        write_output(output_key, processed_schemas)

    except Exception as e:
        error_msg = f"Node {node_id}: Unexpected error retrieving tool schemas for agent '{agent_id}': {e}"
        tool_mgmt_log.exception(error_msg)
        error_output_key = 'openai_tools' if convert_to == 'OpenAI' else 'tool_schemas'
        write_output(error_output_key, [])


def register_custom_tool_node(
    write_output: Callable,
    static_input: dict,
    node_id: str,
    *args, **kwargs
):
    """Node handler to register a custom tool using ToolService."""
    tool_name = static_input.get('tool_name')
    tool_schema_str = static_input.get('tool_schema')
    tool_function_code = static_input.get('tool_function')
    agent_id = kwargs.get('agent_id')
    output_key = 'custom_tool_registration_result'

    if not agent_id:
        error_msg = f"Node {node_id}: Missing 'agent_id' in node execution context."
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name})
        return

    if not all([tool_name, tool_schema_str, tool_function_code]):
        missing_fields = []
        if not tool_name:
            missing_fields.append("'tool_name'")
        if not tool_schema_str:
            missing_fields.append("'tool_schema'")
        if not tool_function_code:
            missing_fields.append("'tool_function'")
        error_msg = f"Node {node_id}: Missing required fields for agent '{agent_id}': {', '.join(missing_fields)}."
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'agent_id': agent_id})
        return

    try:
        tool_schema = json.loads(tool_schema_str)
        if not isinstance(tool_schema, dict):
            raise ValueError("Tool schema must be a JSON object.")
        if tool_schema.get("type") == "function" and "function" in tool_schema:
            if "name" not in tool_schema["function"]:
                 tool_schema["function"]["name"] = tool_name
            elif tool_schema["function"]["name"] != tool_name:
                tool_mgmt_log.warning(f"Node {node_id}: Tool schema for '{tool_name}' has a different function name ('{tool_schema['function']['name']}'). Overwriting with tool_name for consistency.")
                tool_schema["function"]["name"] = tool_name
        else:
            if not (tool_schema.get("type") == "function" and "function" in tool_schema):
                 tool_mgmt_log.warning(f"Node {node_id}: Tool schema for '{tool_name}' is not in OpenAI function format. It will be registered as is, but may not be directly usable by OpenAI models without this structure.")


        compiled_function = _compile_custom_tool_function(tool_function_code, tool_name)
        
        context.tool_service.register_tool(agent_id, tool_name, compiled_function, tool_schema)
        success_msg = f"Custom tool '{tool_name}' registered successfully for agent '{agent_id}'."
        tool_mgmt_log.info(f"Node {node_id}: {success_msg}")
        write_output(output_key, {'success': True, 'message': success_msg, 'tool_name': tool_name, 'agent_id': agent_id})

    except json.JSONDecodeError as jde:
        error_msg = f"Node {node_id}: Invalid JSON in tool_schema for tool '{tool_name}', agent '{agent_id}': {jde}"
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name, 'agent_id': agent_id})
    except (ValueError, TypeError) as ve:
        error_msg = f"Node {node_id}: Error processing custom tool '{tool_name}' for agent '{agent_id}': {ve}"
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name, 'agent_id': agent_id})
    except Exception as e:
        error_msg = f"Node {node_id}: Unexpected error registering custom tool '{tool_name}' for agent '{agent_id}': {e}"
        tool_mgmt_log.exception(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name, 'agent_id': agent_id})


def delete_custom_tool_node(
    write_output: Callable,
    static_input: dict,
    node_id: str,
    *args, **kwargs
):
    """Node handler to delete a custom tool using ToolService."""
    tool_name = static_input.get('tool_name')
    agent_id = kwargs.get('agent_id')
    output_key = 'custom_tool_deletion_result'

    if not agent_id:
        error_msg = f"Node {node_id}: Missing 'agent_id' in node execution context."
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name})
        return

    if not tool_name:
        error_msg = f"Node {node_id}: Missing 'tool_name' in static input for agent '{agent_id}'."
        tool_mgmt_log.error(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'agent_id': agent_id})
        return

    try:
        context.tool_service.delete_tool(agent_id, tool_name)
        success_msg = f"Custom tool '{tool_name}' deleted (or was not registered) for agent '{agent_id}'."
        tool_mgmt_log.info(f"Node {node_id}: {success_msg}")
        write_output(output_key, {'success': True, 'message': success_msg, 'tool_name': tool_name, 'agent_id': agent_id})
    except Exception as e:
        error_msg = f"Node {node_id}: Unexpected error deleting custom tool '{tool_name}' for agent '{agent_id}': {e}"
        tool_mgmt_log.exception(error_msg)
        write_output(output_key, {'success': False, 'error': error_msg, 'tool_name': tool_name, 'agent_id': agent_id})