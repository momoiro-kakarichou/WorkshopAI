from typing import Callable, List, Any, Dict, Optional
from app.utils.utils import create_logger
from app.context import context

conditional_handler_log = create_logger(__name__, entity_name='CONDITIONAL_HANDLER', level=context.log_level)

def filter_by_tool_use_node(
    get_parent_output_by_key: Callable[[str], List[Any]],
    pass_output: Callable,
    request_stop_path: Callable,
    node_id: str,
    *args, **kwargs
):
    """
    Filters workflow execution based on the presence of tool calls in the parent's output.
    If 'openai_completion_result' from a parent node contains non-empty 'tool_calls',
    this node will pass the output. Otherwise, it will request to stop the current path.
    """
    parent_outputs = get_parent_output_by_key('openai_completion_result')
    completion_result: Optional[Dict[str, Any]] = None

    for output_item in parent_outputs:
        if isinstance(output_item, dict) and 'value' in output_item and isinstance(output_item['value'], dict):
            actual_result = output_item['value']
            if isinstance(actual_result.get('tool_calls'), list):
                completion_result = actual_result
                conditional_handler_log.debug(f"Node {node_id}: Found wrapped 'openai_completion_result' with tool_calls.")
                break
        elif isinstance(output_item, dict) and isinstance(output_item.get('tool_calls'), list):
            completion_result = output_item
            conditional_handler_log.debug(f"Node {node_id}: Found direct 'openai_completion_result' with tool_calls.")
            break
        elif isinstance(output_item, dict) and 'key' in output_item and output_item['key'] == 'openai_completion_result' and isinstance(output_item.get('value'), dict):
            actual_result = output_item['value']
            if 'tool_calls' in actual_result:
                completion_result = actual_result
                conditional_handler_log.debug(f"Node {node_id}: Found wrapped 'openai_completion_result' with tool_calls key (may be None/empty).")
                break


    if completion_result:
        tool_calls = completion_result.get('tool_calls')
        if isinstance(tool_calls, list) and len(tool_calls) > 0:
            conditional_handler_log.info(f"Node {node_id}: Tool calls found ({len(tool_calls)}). Passing output.")
            pass_output()
        else:
            conditional_handler_log.info(f"Node {node_id}: No tool calls found or tool_calls list is empty. Requesting stop path.")
            request_stop_path()
    else:
        conditional_handler_log.warning(f"Node {node_id}: No valid 'openai_completion_result' with 'tool_calls' found in parent outputs. Requesting stop path by default.")
        request_stop_path()