import { socket, InterfaceEvent } from './socket.js'; // Added InterfaceEvent
import { showModal } from './common.js';

// Listen for modal events
socket.on(InterfaceEvent.SHOW_MODAL, (data) => {
    console.log(`Received ${InterfaceEvent.SHOW_MODAL} event with data:`, data);

    const {
        name,
        title,
        htmlContent,
        callbackStr,
        allowInteraction,
        customStyles,
        buttonsOff,
        position
    } = data;

    let modalCallback = null;
    if (callbackStr) {
        try {
            // WARNING: Executing arbitrary code received as a string can be a security risk.
            // Ensure that the source of callbackStr is trusted and the content is validated/sanitized
            // if it originates from user input or less trusted sources.
            modalCallback = new Function(callbackStr);
        } catch (error) {
            console.error("Error creating callback function from string:", error);
        }
    }

    showModal({
        name: name,
        title: title,
        htmlContent: htmlContent,
        callback: modalCallback,
        allowInteraction: allowInteraction,
        customStyles: customStyles,
        buttonsOff: buttonsOff,
        position: position
    });
});

// Listen for toastr events
socket.on(InterfaceEvent.SHOW_TOASTR, (data) => {
    console.log(`Received ${InterfaceEvent.SHOW_TOASTR} event with data:`, data);
    const { message, title, level, options } = data;

    if (toastr && typeof toastr[level] === 'function') {
        toastr[level](message, title, options);
    } else {
        console.error(`Invalid toastr level: ${level} or toastr is not available.`);
        toastr.info(message, title, options);
    }
});

console.log('Interface module loaded and listening for modal and toastr events.');