from flask import Blueprint, request, jsonify, current_app
from services.gemini_service import summarize_text, GeminiServiceError

ai_bp = Blueprint('ai_bp', __name__)

@ai_bp.route('/summarize-text', methods=['POST'])
def handle_summarize_text():
    data = request.get_json()
    if not data or not data.get('text'):
        return jsonify({"error": "Missing 'text' in request payload"}), 400

    text_to_summarize = data['text']
    if not isinstance(text_to_summarize, str) or not text_to_summarize.strip():
        return jsonify({"error": "'text' must be a non-empty string"}), 400

    try:
        summary = summarize_text(text_to_summarize)
        return jsonify({"summary": summary}), 200
    except GeminiServiceError as e:
        # Log the error for server-side review
        current_app.logger.error(f"Gemini service error: {str(e)}")
        # Return a generic error to the client
        return jsonify({"error": "Failed to summarize text via AI service.", "details": str(e)}), 502 # 502 Bad Gateway for upstream service error
    except ValueError as ve: # Catch input validation errors from the service
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        # Catch any other unexpected errors
        current_app.logger.error(f"Unexpected error in summarize text endpoint: {str(e)}")
        return jsonify({"error": "An unexpected error occurred."}), 500
