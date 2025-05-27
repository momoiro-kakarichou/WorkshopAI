from typing import Optional, Dict
from app.extensions import socketio
from app.events import SocketIOEventType

def send_show_modal_event(
    name: str, 
    title: str, 
    html_content: str, 
    callback_str: Optional[str] = None, 
    allow_interaction: bool = False, 
    custom_styles: Optional[Dict[str, Dict[str, str]]] = None, 
    buttons_off: bool = False,
    position: Optional[Dict[str, str]] = None
):
    """
    Emits a Socket.IO event to trigger the display of a modal window on the frontend.

    Args:
        name (str): A unique name for the modal.
        title (str): The title of the modal window.
        html_content (str): The HTML content to display within the modal body.
        callback_str (Optional[str]): A string containing JavaScript code for the callback function. 
                                      **Warning:** Security risk. Ensure the source is trusted.
        allow_interaction (bool): If True, allows interaction with the page behind the modal. Defaults to False.
        custom_styles (Optional[Dict[str, Dict[str, str]]]): Custom CSS styles for modal elements.
        buttons_off (bool): If True, hides the default modal footer buttons. Defaults to False.
        position (Optional[Dict[str, str]]): A dictionary of CSS properties to position the modal dialog.
                                             Example: {'top': '10px', 'left': '10px'}, {'bottom': '20px', 'right': '20px'}
                                             If provided, disables dragging. Defaults to None (centered).
    """
    modal_data = {
        'name': name,
        'title': title,
        'htmlContent': html_content,
        'callbackStr': callback_str,
        'allowInteraction': allow_interaction,
        'customStyles': custom_styles or {},
        'buttonsOff': buttons_off,
        'position': position
    }
    socketio.emit(SocketIOEventType.SHOW_MODAL, modal_data)