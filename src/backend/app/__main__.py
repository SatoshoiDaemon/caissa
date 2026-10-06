from . import create_app
from .config import Settings
from .extensions import socketio

if __name__ == "__main__":
    settings = Settings.from_environment()
    socketio.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
        allow_unsafe_werkzeug=True,
    )
