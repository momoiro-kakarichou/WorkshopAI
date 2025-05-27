import { socket, waitForEvent, ChatEvent, MessageEvent } from './socket.js';
import { wrapTextInCustomMarkdown, highlightMessagesCodes, highlightMessageCodes, createQuillEditor } from './format.js'
import { ChatContainerId, MessageHolderClass, MessageClass, EditorClass, Message, Editor } from './templates.js'
import { current_context, MessageRole } from './common.js';

const module_prefix = '[CHAT]:';

export function addMessagesHandlers() {
    $("#send-button").click(function() {
        var text = $("#user-input").val();
        socket.emit(MessageEvent.USER_MESSAGE_SEND, {
            role : MessageRole.USER,
            content : text,
            chat_id: current_context.chat_id
        });
        $("#user-input").val('');
    });
    
    $(ChatContainerId).on('click', '.edit-button', function() {
        var messageHolder = $(this).closest(MessageHolderClass);
        var message = messageHolder.find(MessageClass);
        var editButton = messageHolder.find('.edit-button');
        var saveButton = messageHolder.find('.save-button');
        var cancelButton = messageHolder.find('.cancel-button');
        
        var editorContainer = $(Editor());
        messageHolder.append(editorContainer);
        
        var quill = createQuillEditor(editorContainer[0]);
        
        socket.emit(MessageEvent.GET_MESSAGE_REQUEST, {
            chat_id: current_context.chat_id,
            id: messageHolder.attr('id')
        });
        waitForEvent(MessageEvent.GET_MESSAGE)
        .then((response) => {
            if (response.status === 'success') {
                quill.setText(response.message.content);
                message.hide();
                editorContainer.show();
                editButton.hide();
                saveButton.show();
                cancelButton.show();
            } else {
                console.error(module_prefix, "Error getting message content:", response.message);
                alert(`Error getting message content: ${response.message}`);
                messageHolder.find(EditorClass).remove();
            }
        });
        
        messageHolder.data('quill', quill);
    });
    
    $(ChatContainerId).on('click', '.save-button', function() {
        var messageHolder = $(this).closest(MessageHolderClass);
        
        var quill = messageHolder.data('quill');
        var text = quill.getText();
        
        socket.emit(MessageEvent.EDIT_MESSAGE_REQUEST, {
            chat_id: current_context.chat_id,
            id: messageHolder.attr('id'),
            content: text
        });
        
    });
    
    $(ChatContainerId).on('click', '.cancel-button', function() {
        var messageHolder = $(this).closest(MessageHolderClass);
        var message = messageHolder.find(MessageClass);
        var editButton = messageHolder.find('.edit-button');
        var saveButton = messageHolder.find('.save-button');
        var cancelButton = messageHolder.find('.cancel-button');
        
        socket.emit(MessageEvent.GET_MESSAGE_REQUEST, {
            chat_id: current_context.chat_id,
            id: messageHolder.attr('id'),
        });
        waitForEvent(MessageEvent.GET_MESSAGE)
        .then((response) => {
            if (response.status === 'success') {
                message.html(wrapTextInCustomMarkdown(response.message.content));
                highlightMessageCodes(message);
                MathJax.typesetPromise([message[0]]);
                message.show();
                messageHolder.find(EditorClass).remove();
                editButton.show();
                saveButton.hide();
                cancelButton.hide();
            } else {
                console.error(module_prefix, "Error cancelling edit (failed to get original message):", response.message);
                alert(`Error cancelling edit: ${response.message}`);
                message.show();
                messageHolder.find(EditorClass).remove();
                editButton.show();
                saveButton.hide();
                cancelButton.hide();
            }
        });
    });
    
    $(ChatContainerId).on('click', '.delete-button', function() {
        const messageHolder = $(this).closest(MessageHolderClass);
        
        socket.emit(MessageEvent.REMOVE_MESSAGE_REQUEST, {
            chat_id: current_context.chat_id,
            id: messageHolder.attr('id')
        });
    });
    
    $('#user-input').keydown(function(event) {
        if (event.ctrlKey && event.key === 'Enter') {
            const text = $("#user-input").val();
            socket.emit(MessageEvent.USER_MESSAGE_SEND, {
                role : MessageRole.USER,
                content : text,
                chat_id: current_context.chat_id
            });
            $("#user-input").val('');
        }
    });
    
    
    socket.on(ChatEvent.CHAT, function ( response ) {
        if (response.status === 'success') {
            const chat = response.chat;
            $('#current-chat-name').text(chat.name);
            chat.messages = chat.messages.map((message) => {
                return {
                    ...message,
                    content: wrapTextInCustomMarkdown(message.content),
                };
            });
            const chat_container = $(ChatContainerId);
            chat_container.html(chat.messages.map(Message).join(''));
            current_context.chat_id = chat.id;
            highlightMessagesCodes();
            MathJax.typesetPromise([chat_container[0]]);
            chat_container.scrollTop(chat_container.prop("scrollHeight"));
        } else {
            console.error(module_prefix, "Error loading chat:", response.message);
            alert(`Error loading chat: ${response.message}`);
            $(ChatContainerId).html('<p class="error">Failed to load chat.</p>');
            $('#current-chat-name').text('Error');
            current_context.chat_id = null;
        }
    });
    
    socket.on(MessageEvent.MESSAGE_RECEIVED, function( response ) {
        if (response.status === 'success') {
            const msg = response.message;
            msg.content = wrapTextInCustomMarkdown(msg.content);
            const messageElement = $(Message(msg)).appendTo(ChatContainerId);
            highlightMessageCodes(messageElement);
            MathJax.typesetPromise([messageElement[0]]);
            const chat_container = $(ChatContainerId);
            chat_container.scrollTop(chat_container.prop("scrollHeight"));
        } else {
            console.error(module_prefix, "Error receiving message:", response.message);
            alert(`Error receiving message: ${response.message}`);
            $(ChatContainerId).append(`<div class="message-holder system-error"><p>Failed to process message: ${response.message}</p></div>`);
            const chat_container = $(ChatContainerId);
            chat_container.scrollTop(chat_container.prop("scrollHeight"));
        }
    });
    
    socket.on(MessageEvent.MESSAGE_START, function ( msg ) {
        $(ChatContainerId).append(Message(msg));
    });
    
    socket.on(MessageEvent.MESSAGE_DELTA, function ( message_delta ) {
        var messageHolder = $(ChatContainerId).children().last();
        var message = messageHolder.find(MessageClass);
        message.html(wrapTextInCustomMarkdown(message_delta));
    });
    
    socket.on(MessageEvent.STREAMED_MESSAGE_RECEIVED, function ( msg ) {
        var messageHolder = $(ChatContainerId).children().last();
        var message = messageHolder.find(MessageClass);
        message.html(wrapTextInCustomMarkdown(msg.content));
        highlightMessageCodes(message);
        
        MathJax.typesetPromise([message[0]]);
    });
    
    socket.on(MessageEvent.EDIT_MESSAGE, function(response) {
        const messageHolder = $('#' + response.message_id);
        if (!messageHolder.length) {
            console.warn(module_prefix, `Received EDIT_MESSAGE for non-existent element ID: ${response.message_id}`);
            return;
        }
        const message = messageHolder.find(MessageClass);
        const editButton = messageHolder.find('.edit-button');
        const saveButton = messageHolder.find('.save-button');
        const cancelButton = messageHolder.find('.cancel-button');
        
        messageHolder.find(EditorClass).remove();
        messageHolder.removeData('quill');
        
        if (response.status === 'success') {
            console.log(module_prefix, `Edit confirmed for message ${response.message_id}. Fetching updated content.`);
            socket.emit(MessageEvent.GET_MESSAGE_REQUEST, {
                chat_id: current_context.chat_id,
                id: response.message_id
            });
            waitForEvent(MessageEvent.GET_MESSAGE)
            .then((getMessageResponse) => {
                if (getMessageResponse.status === 'success' && getMessageResponse.message) {
                    message.html(wrapTextInCustomMarkdown(getMessageResponse.message.content));
                    highlightMessageCodes(message);
                    MathJax.typesetPromise([message[0]]);
                    console.log(module_prefix, `Message ${response.message_id} updated successfully.`);
                } else {
                    console.error(module_prefix, `Failed to fetch updated content for message ${response.message_id} after edit:`, getMessageResponse.message);
                    alert(`Error fetching updated message content: ${getMessageResponse.message}`);
                }
                message.show();
                editButton.show();
                saveButton.hide();
                cancelButton.hide();
            });
        } else if (response.status === 'error') {
            console.error(module_prefix, "Error saving message (via socket event):", response.message);
            alert(`Error saving message: ${response.message}`);
            message.show();
            editButton.show();
            saveButton.hide();
            cancelButton.hide();
        }
    });
    
    socket.on(MessageEvent.REMOVE_MESSAGE, function(response) {
        if (response.status === 'success') {
            const messageHolder = $('#' + response.message_id);
            if (messageHolder.length) {
                messageHolder.remove();
                console.log(module_prefix, `Message ${response.message_id} removed successfully confirmed by server (via socket event).`);
            } else {
                console.warn(module_prefix, `Received REMOVE_MESSAGE for non-existent element ID: ${response.message_id}`);
            }
        } else if (response.status === 'error') {
            console.error(module_prefix, "Error removing message (via socket event):", response.message);
            alert(`Error removing message ${response.message_id || ''}: ${response.message}`);
        }
    });
}