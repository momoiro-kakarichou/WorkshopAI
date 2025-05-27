from typing import Callable
import json
from app.services import api_service
from app.context import context
from app.constants import MessageRole
from app.api.chat_completions_api import OpenAICompletions
from app.utils.utils import create_logger
from app.helpers.openai_helpers import openai_stream_to_chat

openai_handler_log = create_logger(__name__, entity_name='OPENAI', level=context.log_level)

def convert_to_openai_chat_history_node(write_output: Callable, get_parent_output_by_key: Callable, *args, **kwargs):
    parent_outputs = get_parent_output_by_key('chat_history')
    chat_history_key = 'chat_history'
    chat_history_content = None

    for content in parent_outputs:
        if isinstance(content, list):
            chat_history_content = content
            break

    if chat_history_content is None or len(chat_history_content) == 0:
        write_output(chat_history_key, [])
        return

    openai_history = []
    for message in chat_history_content:
        role = message.get('role')
        content = message.get('content')

        openai_role = None
        if role == MessageRole.USER:
            openai_role = 'user'
        elif role == MessageRole.ASSISTANT:
            openai_role = 'assistant'
        elif role == MessageRole.SYSTEM:
            openai_role = 'system'
        elif role == MessageRole.TOOL:
            openai_role = 'tool'

        if openai_role and content is not None:
            openai_message = {"role": openai_role, "content": str(content)}            
            if role == MessageRole.TOOL and 'tool_call_id' in message:
                 openai_message['tool_call_id'] = message['tool_call_id']

            openai_history.append(openai_message)

    write_output('openai_chat_history', openai_history)

def openai_chat_completion_generator_node(
    write_output: Callable,
    get_parent_output_by_key: Callable,
    static_input: dict,
    node_id: str,
    *args, **kwargs
):
    """
    Node handler that initiates and consumes a streaming chat completion from OpenAI API,
    optionally redirects events to a helper function during consumption,
    and outputs the final aggregated results.

    Inputs:
        - Expects 'openai_chat_history' from a parent node via get_parent_output_by_key.
        - Reads configuration like 'model', 'max_tokens', 'api_endpoint', 'api_key',
          and optionally 'helper_function_name' from static_input.

    Outputs:
        - 'openai_completion_result': A dictionary containing the final results:
            - 'content' (str): The aggregated text content.
            - 'tool_calls' (list): Completed tool calls.
            - 'metadata' (dict): Usage stats and finish reason.
            - 'error' (str | None): Error message if failed, None otherwise.
    """
    from app.events import DataEventType, DataEvent

    openai_history_outputs = get_parent_output_by_key('openai_chat_history')
    openai_chat_history = None
    output_key = 'openai_completion_result'
    api_call_args_key_in_dict = 'api_call_args'
    content_key_in_dict = 'content'
    tool_calls_key_in_dict = 'tool_calls'
    metadata_key_in_dict = 'metadata'
    error_key_in_dict = 'error'
    chat_id = context.chat_id

    for content in openai_history_outputs:
        if isinstance(content, list):
            openai_chat_history = content
            break

    openai_tools_outputs = get_parent_output_by_key('openai_tools')
    openai_tools = None
    for content in openai_tools_outputs:
        if isinstance(content, list):
            openai_tools = content
            openai_handler_log.info(f"Node {node_id}: Found openai_tools input with {len(openai_tools)} tools.")
            break

    if not openai_chat_history:
        error_msg = f"Node {node_id}: Missing 'openai_chat_history' input."
        openai_handler_log.error(error_msg)
        result_dict = {
            content_key_in_dict: None,
            tool_calls_key_in_dict: [],
            metadata_key_in_dict: None,
            api_call_args_key_in_dict: None,
            error_key_in_dict: error_msg
        }
        write_output(output_key, result_dict)
        return

    api_tag = static_input.get('api_tag')
    max_tokens = int(static_input.get('max_tokens', 1024))
    temperature = float(static_input.get('temperature', 1.0))
    top_p = float(static_input.get('top_p', 1.0))
    stop_sequences_str = static_input.get('stop_sequences', '[]')
    stop_sequences = []
    try:
        parsed_stop_sequences = json.loads(stop_sequences_str)
        if isinstance(parsed_stop_sequences, list):
            stop_sequences = parsed_stop_sequences
        else:
            openai_handler_log.warning(f"Node {node_id}: 'stop_sequences' was not a valid JSON list, defaulting to []. Value: {stop_sequences_str}")
    except json.JSONDecodeError:
        openai_handler_log.warning(f"Node {node_id}: Failed to parse 'stop_sequences' as JSON, defaulting to []. Value: {stop_sequences_str}")

    stream_response = static_input.get('stream', True)
    helper_func_name = static_input.get('helper_function_name')
    extra_params = {k: v for k, v in static_input.items() if k not in [
        'api_tag', 'model', 'max_tokens', 'temperature',
        'top_p', 'stop_sequences', 'stream', 'helper_function_name'
    ]}

    api_endpoint = None
    api_key = None
    model = None
    api_config = None

    if api_tag:
        try:
            api_config = api_service.get_random_api_by_tag(tag=api_tag, fallback_to_default=True)
            if api_config:
                api_endpoint = api_config.api_url
                api_key = api_config.api_key
                model = api_config.model
                openai_handler_log.info(f"Node {node_id}: Using API '{api_config.name}' (ID: {api_config.id}, Model: {model}) selected by tag '{api_tag}'.")
            else:
                openai_handler_log.warning(f"Node {node_id}: No API configuration found for tag '{api_tag}' (including fallback).")
        except Exception as e:
            openai_handler_log.error(f"Node {node_id}: Error fetching API configuration for tag '{api_tag}': {e}")
    else:
        openai_handler_log.warning(f"Node {node_id}: 'api_tag' not provided in static_input. Cannot select API by tag.")

    if not api_endpoint or not model:
        error_msg = ""
        if not api_tag:
            error_msg = f"Node {node_id}: Missing API configuration: 'api_tag' was not provided in static_input."
        elif not api_config:
            error_msg = f"Node {node_id}: Missing API configuration: No API found for tag '{api_tag}' (including fallback)."
        else:
            error_msg = f"Node {node_id}: Incomplete API configuration for tag '{api_tag}'. Endpoint or model is missing."

        openai_handler_log.error(error_msg)
        result_dict = {
            content_key_in_dict: None,
            tool_calls_key_in_dict: [],
            metadata_key_in_dict: None,
            api_call_args_key_in_dict: None,
            error_key_in_dict: error_msg
        }
        write_output(output_key, result_dict)
        return

    try:
        openai_client = OpenAICompletions(endpoint=api_endpoint, api_key=api_key)
        api_call_args = {
            "messages": openai_chat_history,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stop_sequences": stop_sequences,
            "stream": stream_response,
            **extra_params
        }

        if openai_tools:
            api_call_args["tools"] = openai_tools
            api_call_args["tool_choice"] = "auto"
            openai_handler_log.info(f"Node {node_id}: Passing {len(openai_tools)} tools to OpenAI API.")

        completion_stream = openai_client.create(**api_call_args)

        helper_func = None
        helper_params = {}
        start_action = 'add'
        if helper_func_name and helper_func_name != 'None':
            helper_map = {
                'openai_stream_to_chat_add': {'func': openai_stream_to_chat, 'action': 'add'},
                'openai_stream_to_chat_swipe': {'func': openai_stream_to_chat, 'action': 'swipe'},
                'openai_stream_to_chat_append': {'func': openai_stream_to_chat, 'action': 'append'}
            }

            if helper_func_name in helper_map:
                helper_info = helper_map[helper_func_name]
                helper_func = helper_info['func']
                start_action = helper_info['action']
                if chat_id:
                    helper_params = {'chat_id': chat_id}
                else:
                    openai_handler_log.warning(f"Node {node_id}: Helper '{helper_func_name}' requires 'chat_id', but it was not found in context. Helper disabled.")
                    helper_func = None
            else:
                helper_func = globals().get(helper_func_name)

            if helper_func and not callable(helper_func):
                log_msg = f"Node {node_id}: Specified helper function '{helper_func_name}' not found or not callable. Redirection disabled."
                openai_handler_log.warning(log_msg)
                helper_func = None
            elif helper_func:
                openai_handler_log.info(f"Node {node_id}: Will redirect stream events to helper function '{helper_func_name}'{f' for chat_id {chat_id}' if chat_id else ''}.")
        elif helper_func_name == 'None':
            openai_handler_log.info(f"Node {node_id}: Helper function explicitly set to None. No redirection will occur.")
            helper_func = None

        final_content = ""
        completed_tool_calls = []
        final_metadata = None
        stream_error = None
        temp_content_buffer = ""

        log_message_type = "stream" if stream_response else "non-stream"
        openai_handler_log.info(f"Node {node_id}: Consuming OpenAI {log_message_type}. Helper: {'Enabled' if helper_func else 'Disabled'}")

        try:
            for event in completion_stream:
                if helper_func:
                    try:
                        event_to_helper = event
                        if not stream_response and event.type == DataEventType.MESSAGE_COMPLETE:
                            if helper_func_name and helper_func_name != 'None':
                                helper_func(DataEvent(DataEventType.MESSAGE_START, None, event.quiet), helper_params, start_action=start_action)
                        
                        helper_func(event_to_helper, helper_params, start_action=start_action)
                        
                        if not stream_response and event.type == DataEventType.MESSAGE_COMPLETE:
                            if helper_func_name and helper_func_name != 'None':
                                helper_func(DataEvent(DataEventType.MESSAGE_END, None, event.quiet), helper_params, start_action=start_action)

                    except Exception as e_helper:
                        log_msg = f"Node {node_id}: Error calling helper function '{getattr(helper_func, '__name__', 'unknown')}' with action '{start_action}': {e_helper}"
                        openai_handler_log.error(log_msg, exc_info=True)

                if event.type == DataEventType.MESSAGE_DELTA and stream_response:
                    if isinstance(event.data, str):
                         temp_content_buffer = event.data
                elif event.type == DataEventType.STREAMED_MESSAGE_COMPLETE and stream_response:
                    final_content = event.data
                    openai_handler_log.debug(f"Node {node_id}: Received STREAMED_MESSAGE_COMPLETE.")
                elif event.type == DataEventType.MESSAGE_COMPLETE and not stream_response:
                    final_content = event.data
                    openai_handler_log.debug(f"Node {node_id}: Received MESSAGE_COMPLETE (non-streaming).")
                elif event.type == DataEventType.TOOL_CALL_COMPLETE:
                    completed_tool_calls.append(event.data)
                    openai_handler_log.debug(f"Node {node_id}: Received TOOL_CALL_COMPLETE: {event.data.get('id')}")
                elif event.type == DataEventType.METADATA_RECEIVED:
                    final_metadata = event.data
                    openai_handler_log.debug(f"Node {node_id}: Received METADATA_RECEIVED.")
                elif event.type == DataEventType.ERROR:
                    stream_error = str(event.data)
                    openai_handler_log.error(f"Node {node_id}: Error received from API: {stream_error}")

            if stream_response and not final_content and temp_content_buffer:
                 final_content = temp_content_buffer
                 openai_handler_log.warning(f"Node {node_id}: Using buffered content as final_content since STREAMED_MESSAGE_COMPLETE was missing (streaming).")
            elif not stream_response and not final_content:
                 openai_handler_log.warning(f"Node {node_id}: No content received from non-streaming call.")


        except Exception as e_consume:
            error_msg = f"Node {node_id}: Exception while consuming stream: {e_consume}"
            openai_handler_log.error(error_msg, exc_info=True)
            stream_error = error_msg

        result_dict = {}
        if stream_error:
            result_dict = {
                content_key_in_dict: final_content or "",
                tool_calls_key_in_dict: completed_tool_calls,
                metadata_key_in_dict: final_metadata,
                api_call_args_key_in_dict: api_call_args,
                error_key_in_dict: stream_error
            }
            openai_handler_log.info(f"Node {node_id}: API call processing finished with error.")
        else:
            result_dict = {
                content_key_in_dict: final_content,
                tool_calls_key_in_dict: completed_tool_calls,
                metadata_key_in_dict: final_metadata,
                api_call_args_key_in_dict: api_call_args,
                error_key_in_dict: None
            }
            openai_handler_log.info(f"Node {node_id}: API call processing finished successfully. Content length: {len(final_content if final_content else '')}, Tool calls: {len(completed_tool_calls)}")

        write_output(output_key, result_dict)


    except Exception as e_setup:
        error_msg = f"Node {node_id}: Error setting up OpenAI API call: {e_setup}"
        openai_handler_log.error(error_msg, exc_info=True)
        result_dict = {
            content_key_in_dict: None,
            tool_calls_key_in_dict: [],
            metadata_key_in_dict: None,
            error_key_in_dict: error_msg
        }
        write_output(output_key, result_dict)

def execute_tool_call_node(
    write_output: Callable,
    get_parent_output_by_key: Callable,
    node_id: str,
    *args, **kwargs
):
    """
    Node handler that processes tool calls from a previous OpenAI completion node.
    It executes the requested tools using ToolService and outputs the results
    in the OpenAI tool message format.

    Inputs:
        - Expects 'openai_completion_result' from a parent node via get_parent_output_by_key.
          This dictionary should contain a 'tool_calls' list.

    Outputs:
        - 'tool_results': A list of dictionaries, each representing a tool result message
                          formatted for OpenAI (e.g., {'role': 'tool', 'content': '...', 'tool_call_id': '...'}).
    """
    parent_outputs = get_parent_output_by_key('openai_completion_result')
    output_key = 'tool_results'
    tool_results = []
    completion_result = None
    agent_id = kwargs.get('agent_id')

    if not agent_id:
        openai_handler_log.error(f"Node {node_id}: Missing 'agent_id' in node execution context for tool execution.")
        write_output(output_key, [])
        return

    for output in parent_outputs:
        if isinstance(output, dict):
            completion_result = output
            break

    if not completion_result:
        openai_handler_log.warning(f"Node {node_id} (Agent: {agent_id}): No valid 'openai_completion_result' dictionary found in parent outputs.")
        write_output(output_key, [])
        return

    tool_calls = completion_result.get('tool_calls')
    error_in_completion = completion_result.get('error')

    if error_in_completion:
        openai_handler_log.warning(f"Node {node_id} (Agent: {agent_id}): Skipping tool execution due to error in parent completion: {error_in_completion}")
        write_output(output_key, [])
        return

    if not tool_calls or not isinstance(tool_calls, list):
        openai_handler_log.info(f"Node {node_id} (Agent: {agent_id}): No tool calls found in the completion result.")
        write_output(output_key, [])
        return

    openai_handler_log.info(f"Node {node_id} (Agent: {agent_id}): Found {len(tool_calls)} tool call(s) to execute.")


    for tool_call in tool_calls:
        tool_call_id = tool_call.get('id')
        function_call = tool_call.get('function')

        if not tool_call_id or not function_call:
            openai_handler_log.warning(f"Node {node_id} (Agent: {agent_id}): Skipping invalid tool call object: {tool_call}")
            continue

        tool_name = function_call.get('name')
        tool_args_json = function_call.get('arguments')

        if not tool_name or tool_args_json is None:
            openai_handler_log.warning(f"Node {node_id} (Agent: {agent_id}): Skipping tool call with missing name or arguments: {tool_call}")
            continue

        try:
            result = context.tool_service.execute_tool(agent_id, tool_name, tool_args_json)
            content = json.dumps(result) if not isinstance(result, str) else result
            tool_results.append({
                "role": "tool",
                "content": content,
                "tool_call_id": tool_call_id
            })
            openai_handler_log.info(f"Node {node_id} (Agent: {agent_id}): Successfully executed tool '{tool_name}' with ID '{tool_call_id}'.")

        except ValueError as ve:
            openai_handler_log.error(f"Node {node_id} (Agent: {agent_id}): Value error executing tool '{tool_name}' (ID: {tool_call_id}): {ve}")
            tool_results.append({
                "role": "tool",
                "content": f"Error executing tool '{tool_name}': {ve}",
                "tool_call_id": tool_call_id
            })
        except Exception as e:
            openai_handler_log.exception(f"Node {node_id} (Agent: {agent_id}): Exception executing tool '{tool_name}' (ID: {tool_call_id}): {e}")
            tool_results.append({
                "role": "tool",
                "content": f"Error during execution of tool '{tool_name}': {e}",
                "tool_call_id": tool_call_id
            })

    openai_handler_log.info(f"Node {node_id} (Agent: {agent_id}): Finished processing tool calls. Writing {len(tool_results)} results.")
    write_output(output_key, tool_results)

def append_tool_results_to_history_node(
    write_output: Callable,
    get_parent_output_by_key: Callable,
    node_id: str,
    *args, **kwargs
):
    """
    Appends the assistant's message (if it contained tool_calls) and the
    tool_results to the openai_chat_history.

    Inputs:
        - 'openai_completion_result': The result from an OpenAI completion,
                                      which should contain 'api_call_args' with 'messages' (the history)
                                      and potentially 'tool_calls'.
        - 'tool_results': The results of executing tools.

    Outputs:
        - 'openai_chat_history': The updated OpenAI chat history.
    """
    completion_result_outputs = get_parent_output_by_key('openai_completion_result')
    tool_results_outputs = get_parent_output_by_key('tool_results')

    updated_history = []
    output_key = 'openai_chat_history'

    completion_result = None
    for res_output in completion_result_outputs:
        if isinstance(res_output, dict):
            completion_result = res_output
            break

    if not completion_result:
        openai_handler_log.warning(f"Node {node_id}: Missing 'openai_completion_result' input. Cannot retrieve history or tool calls. Outputting empty history.")
        write_output(output_key, [])
        return

    api_call_args = completion_result.get('api_call_args')
    if not isinstance(api_call_args, dict):
        openai_handler_log.warning(f"Node {node_id}: 'api_call_args' not found or not a dict in 'openai_completion_result'. Outputting empty history.")
        write_output(output_key, [])
        return

    current_history = api_call_args.get('messages')
    if not isinstance(current_history, list):
        openai_handler_log.warning(f"Node {node_id}: 'messages' (chat history) not found or not a list in 'api_call_args'. Outputting empty history.")
        write_output(output_key, [])
        return
    
    updated_history.extend(list(current_history))

    completion_result = None
    for res_output in completion_result_outputs:
        if isinstance(res_output, dict):
            completion_result = res_output
            break

    tool_results = None
    for tr_output in tool_results_outputs:
        if isinstance(tr_output, list):
            tool_results = tr_output
            break

    assistant_message_appended = False
    if completion_result:
        tool_calls = completion_result.get('tool_calls')
        if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
            assistant_message = {
                "role": "assistant",
                "content": None,
                "tool_calls": tool_calls
            }
            if not (updated_history and updated_history[-1] == assistant_message):
                 updated_history.append(assistant_message)
                 assistant_message_appended = True
                 openai_handler_log.info(f"Node {node_id}: Appended assistant message with {len(tool_calls)} tool_calls to history.")
            else:
                openai_handler_log.info(f"Node {node_id}: Assistant message with tool_calls already present in history. Not appending.")


    if tool_results and isinstance(tool_results, list) and len(tool_results) > 0:
        if not assistant_message_appended and completion_result:
            openai_handler_log.warning(f"Node {node_id}: Appending tool_results, but no corresponding assistant message with tool_calls was appended from completion_result. This might lead to API errors.")

        for res in tool_results:
            if isinstance(res, dict) and "tool_call_id" in res and "content" in res:
                tool_message = {
                    "role": "tool",
                    "tool_call_id": res["tool_call_id"],
                    "content": res["content"]
                }
                append_tool_msg = True
                if updated_history:
                    last_assistant_idx = -1
                    for i in range(len(updated_history) - 1, -1, -1):
                        if updated_history[i].get("role") == "assistant":
                            last_assistant_idx = i
                            break
                    
                    if last_assistant_idx != -1:
                        for i in range(last_assistant_idx + 1, len(updated_history)):
                            if updated_history[i] == tool_message:
                                append_tool_msg = False
                                break
                
                if append_tool_msg:
                    updated_history.append(tool_message)
                    openai_handler_log.info(f"Node {node_id}: Appended tool result for ID {res['tool_call_id']} to history.")
                else:
                    openai_handler_log.info(f"Node {node_id}: Tool result for ID {res['tool_call_id']} already present in history. Not appending.")
            else:
                openai_handler_log.warning(f"Node {node_id}: Skipping invalid tool result item: {res}")
    elif tool_results is not None:
        openai_handler_log.info(f"Node {node_id}: 'tool_results' input was present but empty. No tool results to append.")


    openai_handler_log.info(f"Node {node_id}: Writing updated history with {len(updated_history)} messages.")
    write_output(output_key, updated_history)