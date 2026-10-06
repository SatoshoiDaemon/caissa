from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(413)
    def handle_payload_too_large(_error):
        return jsonify({"error": "request payload is too large"}), 413

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        # Preserve Flask's status for unknown routes and other HTTP errors;
        # the generic Exception handler must not turn a 404 into a 500.
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(_error):
        app.logger.exception("Unhandled application error")
        return jsonify({"error": "internal server error"}), 500
