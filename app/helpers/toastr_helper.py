from typing import Optional
from app.extensions import socketio
from app.events import SocketIOEventType

def show_toastr_message(
    message: str, 
    title: Optional[str] = None, 
    level: str = 'info', 
    options: Optional[dict] = None
):
    """
    Emits a Socket.IO event to trigger the display of a toastr message on the frontend.

    Args:
        message (str): The main message content for the toastr.
        title (Optional[str]): The title for the toastr. Defaults to None.
        level (str): The level of the toastr (e.g., 'info', 'success', 'warning', 'error'). 
                     Defaults to 'info'.
        options (Optional[dict]): Additional toastr options (see toastr.js documentation). 
                                  Defaults to None.
    """
    toastr_data = {
        'message': message,
        'title': title,
        'level': level,
        'options': options or {}
    }
    socketio.emit(SocketIOEventType.SHOW_TOASTR, toastr_data)