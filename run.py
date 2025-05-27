import sys
import webbrowser
import signal
import os
from threading import Timer
from app import create_app, socketio
from dotenv import load_dotenv

def open_browser():
    webbrowser.open_new(f"http://{os.getenv('HOST', '127.0.0.1')}:{int(os.getenv('PORT', 5000))}")

shutting_down = False

def shutdown_handler(signum, frame):
    global shutting_down
    if shutting_down:
        print("\nForcing immediate shutdown...")
        os._exit(1)
    else:
        shutting_down = True
        print("\nShutting down Workshop AI... (Press CTRL+C again to force)")
        sys.exit(0)

if __name__ == "__main__":
    print("Workshop AI starting...")
    load_dotenv(override=True)
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *x: None

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    app = create_app()
    print("Workshop AI started.")
    if os.getenv("OPEN_BROWSER", "True").lower() == "true":
        Timer(0.5, open_browser).start()
    
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    print(f"Application is running on: http://{host}:{port}")
    socketio.run(app, host=host, port=port)
