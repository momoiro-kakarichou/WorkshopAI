from app.extensions import socketio, log
from app.events import DataEventType, SocketIOEventType
from app.constants import MessageRole
from app.services import chat_service
from app.helpers.toastr_helper import show_toastr_message

EVENT_TYPE_MAP = {
    DataEventType.MESSAGE_START: SocketIOEventType.MESSAGE_START,
    DataEventType.MESSAGE_DELTA: SocketIOEventType.MESSAGE_DELTA,
    DataEventType.MESSAGE_END: SocketIOEventType.MESSAGE_END,
    DataEventType.MESSAGE_COMPLETE: SocketIOEventType.STREAMED_MESSAGE_RECEIVED,
    DataEventType.STREAMED_MESSAGE_COMPLETE: SocketIOEventType.STREAMED_MESSAGE_RECEIVED,
    DataEventType.ERROR: SocketIOEventType.ERROR,
    DataEventType.INFO: None,
    DataEventType.TOOL_CALL_DELTA: None,
    DataEventType.TOOL_CALL_COMPLETE: None,
    DataEventType.METADATA_RECEIVED: None,
}

def openai_stream_to_chat(event, params: dict, start_action: str = 'add'):
    """
    Helper function to redirect OpenAI stream events (streaming or non-streaming)
    to the appropriate chat via SocketIO.
    Performs an action (add, swipe, append) on MESSAGE_START or MESSAGE_COMPLETE (non-streaming)
    and updates the message on STREAMED_MESSAGE_COMPLETE or MESSAGE_COMPLETE.

    Args:
        event: The DataEvent object from the OpenAI stream.
        params (dict): A dictionary containing necessary parameters, must include 'chat_id'.
                       Is used to store temporary state like 'temp_message_id'.
        start_action (str): Action to perform on message creation ('add', 'swipe', or 'append'). Defaults to 'add'.
    """
    chat_id = params.get('chat_id')
    if not chat_id:
        log.error("openai_stream_to_chat: Missing 'chat_id' in params. Cannot process event.")
        return

    temp_message_id_key = 'temp_message_id'
    original_content_key = 'original_content'

    def _perform_start_action(current_start_action: str):
        """Handles the creation/selection of a message and emits MESSAGE_START or SWIPE."""
        nonlocal start_action
        try:
            if current_start_action == 'append':
                head_message_dto = chat_service.get_head_message_dto(chat_id)
                if not head_message_dto:
                    log.error(f"openai_stream_to_chat: Cannot append. Head message not found for chat {chat_id}. Falling back to 'add'.")
                    start_action = 'add'
                    current_start_action = 'add'
                else:
                    params[temp_message_id_key] = head_message_dto.id
                    params[original_content_key] = head_message_dto.content
                    log.info(f"openai_stream_to_chat: Appending to message {head_message_dto.id} for chat {chat_id}.")
                    message_dict = head_message_dto.model_dump(mode='json')
                    socketio.emit(SocketIOEventType.MESSAGE_START, message_dict)
                    log.debug(f"DTO for message {head_message_dto.id} (action: append) to chat_id '{chat_id}'...")
                    return True

            if current_start_action == 'add' or current_start_action == 'swipe':
                message_data = {'role': MessageRole.ASSISTANT, 'content': ""}
                if current_start_action == 'add':
                    new_message_dto = chat_service.add_message_to_chat(chat_id=chat_id, message_data=message_data)
                    action_verb = "Created"
                    socket_event = SocketIOEventType.MESSAGE_START
                elif current_start_action == 'swipe':
                    new_message_dto = chat_service.swipe_message_in_chat(chat_id=chat_id, message_data=message_data)
                    action_verb = "Swiped to"
                    socket_event = SocketIOEventType.SWIPE
                else:
                    log.error(f"openai_stream_to_chat: Invalid start_action '{current_start_action}' in _perform_start_action.")
                    return False

                params[temp_message_id_key] = new_message_dto.id
                log.info(f"openai_stream_to_chat: {action_verb} placeholder message {new_message_dto.id} for chat {chat_id}.")
                message_dict = new_message_dto.model_dump(mode='json')
                socketio.emit(socket_event, message_dict)
                log.debug(f"DTO for message {new_message_dto.id} (action: {current_start_action}) to chat_id '{chat_id}'...")
                return True
            return False

        except Exception as e_create:
            log.error(f"openai_stream_to_chat: Failed to '{current_start_action}' placeholder/head message for chat {chat_id}: {e_create}", exc_info=True)
            try:
                socketio.emit(SocketIOEventType.ERROR, {'message': f"Failed to create/select assistant message: {e_create}"})
            except Exception as e_emit_err:
                log.error(f"openai_stream_to_chat: Failed to emit creation error event to chat {chat_id}: {e_emit_err}")
            return False

    def _handle_final_message_update(final_content_data: str):
        """Handles updating the message with final content and emitting STREAMED_MESSAGE_RECEIVED."""
        temp_message_id = params.pop(temp_message_id_key, None)
        original_content = params.pop(original_content_key, "") if start_action == 'append' else ""

        if not temp_message_id:
            log.error(f"openai_stream_to_chat: Received final message content for chat {chat_id} but no temp_message_id was found. Cannot update.")
            socketio.emit(SocketIOEventType.ERROR, {'message': "Internal error: Could not find message to update."})
            return

        if final_content_data is not None:
            try:
                content_to_save = final_content_data
                if start_action == 'append':
                    content_to_save = (original_content + "\n" + final_content_data).strip()
                    log.info(f"openai_stream_to_chat: Appending content to message {temp_message_id} for chat {chat_id}.")
                
                updated_message_dto = chat_service.edit_message_content(message_id=temp_message_id, new_content=content_to_save)
                
                log_action = "Updated" if start_action != 'append' else "Appended to"
                log.info(f"openai_stream_to_chat: {log_action} message {temp_message_id} with final content for chat {chat_id}. Length: {len(content_to_save)}")

                socket_event_type = SocketIOEventType.STREAMED_MESSAGE_RECEIVED
                message_dict = updated_message_dto.model_dump(mode='json')
                log.debug(f"Emitting '{socket_event_type}' with DTO for message {updated_message_dto.id} (action: {start_action}) to chat_id '{chat_id}'...")
                socketio.emit(socket_event_type, message_dict)

            except Exception as e_update_emit:
                log.error(f"openai_stream_to_chat: Failed to update/append or emit completed message {temp_message_id} for chat {chat_id} (action: {start_action}): {e_update_emit}", exc_info=True)
                try:
                    socketio.emit(SocketIOEventType.ERROR, {'message': f"Failed to update assistant message {temp_message_id}: {e_update_emit}"})
                except Exception as e_emit_err:
                    log.error(f"openai_stream_to_chat: Failed to emit update error event to chat {chat_id}: {e_emit_err}")
        else:
            log.warning(f"openai_stream_to_chat: Received final message event for chat {chat_id}, message {temp_message_id}, but content was None. Message may remain as placeholder or previous append state.")
            if start_action == 'append' and original_content:
                 log.info(f"openai_stream_to_chat: Append action for {temp_message_id} received None content. Original content was '{original_content[:50]}...'. No update action taken beyond initial placeholder.")
            elif start_action != 'append':
                 log.info(f"openai_stream_to_chat: Add/Swipe action for {temp_message_id} received None content. Message remains empty placeholder.")


    try:
        if event.type == DataEventType.MESSAGE_START:
            _perform_start_action(start_action)

        elif event.type == DataEventType.MESSAGE_DELTA:
            socket_event_type = SocketIOEventType.MESSAGE_DELTA
            data_to_emit = event.data
            log.debug(f"Emitting '{socket_event_type}' to chat_id '{chat_id}'...")
            socketio.emit(socket_event_type, data_to_emit)

        elif event.type == DataEventType.STREAMED_MESSAGE_COMPLETE:
            _handle_final_message_update(event.data)
        
        elif event.type == DataEventType.MESSAGE_COMPLETE:
            if not params.get(temp_message_id_key):
                if not _perform_start_action(start_action):
                    log.error(f"openai_stream_to_chat: Failed to perform start action for non-streaming MESSAGE_COMPLETE on chat {chat_id}. Aborting.")
                    return
            _handle_final_message_update(event.data)

        elif event.type == DataEventType.MESSAGE_END:
            socket_event_type = SocketIOEventType.MESSAGE_END
            log.debug(f"Emitting '{socket_event_type}' to chat_id '{chat_id}'...")
            socketio.emit(socket_event_type)

        elif event.type == DataEventType.ERROR:
            error_message_content = event.data.get('message', str(event.data)) if isinstance(event.data, dict) else str(event.data)
            log.error(f"openai_stream_to_chat: Received API error for chat {chat_id}: {error_message_content}")
            show_toastr_message(message=error_message_content, title="API Error", level='error')

        elif event.type == DataEventType.INFO:
            log.info(f"OpenAI API Info (ChatID: {chat_id}): {event.data}")

    except Exception as e_general:
        log.error(f"openai_stream_to_chat: Unexpected error processing event type {event.type} for chat {chat_id}: {e_general}", exc_info=True)
        try:
            socketio.emit(SocketIOEventType.ERROR, {'message': f"Unexpected error processing API event: {e_general}"})
        except Exception as e_emit_err:
            log.error(f"openai_stream_to_chat: Failed to emit general error event to chat {chat_id}: {e_emit_err}")
