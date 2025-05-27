from typing import Callable
from app.helpers.chat_helpers import get_chat_history

def get_chat_history_node(write_output: Callable, *args, **kwargs):
    chat_history = get_chat_history()
    key = 'chat_history'
    content = chat_history
    write_output(key, content)

def squash_roles_chat_history_node(write_output: Callable, get_parent_output_by_key: Callable, static_input: dict, *args, **kwargs):
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

    squashed_history = []
    current_squashed_message = chat_history_content[0].copy()
    squashed_history.append(current_squashed_message)

    for i in range(1, len(chat_history_content)):
        next_message = chat_history_content[i]
        last_squashed_message = squashed_history[-1]

        if next_message.get('role') == last_squashed_message.get('role'):
            last_content = last_squashed_message.get('content', '')
            next_content = next_message.get('content', '')
            separator = static_input.get('separator', '\n')
            effective_separator = separator if isinstance(last_content, str) and last_content and isinstance(next_content, str) and next_content else ""
            merged_content = f"{last_content}{effective_separator}{next_content}"
            last_squashed_message['content'] = merged_content
        else:
            squashed_history.append(next_message.copy())

    write_output(chat_history_key, squashed_history)
    