from flask import Blueprint, request, jsonify, current_app
from services.gemini_service import (
    summarize_text,
    analyze_notes_text,
    perform_global_search,
    search_external_grants_via_ai,
    match_researchers_to_grant_via_ai,
    generate_grant_intro_email_via_ai, # Added this
    GeminiServiceError
)
import json # For JSONDecodeError

# Import models and serializers (or assume they are accessible)
# This is a bit tricky as serializers are in each route file.
# For this exercise, we might need to either:
# 1. Re-define simplified serializers here.
# 2. Assume a refactor where serializers are in a shared module.
# 3. Temporarily import directly from other route files (can lead to circular dependencies if not careful).

# Let's try to import them directly, assuming it works for this context.
# If not, simplified local serializers would be the fallback.
from models.models import Researcher, Lab, Project, ComputeResource, Grant, Note
from routes.researchers import researcher_to_json, note_to_json # Assuming these can be imported
from routes.labs import lab_to_json
from routes.projects import project_to_json
from routes.compute_resources import compute_resource_to_json
from routes.grants import grant_to_json


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

@ai_bp.route('/analyze-notes', methods=['POST'])
def handle_analyze_notes():
    data = request.get_json()
    if not data or not data.get('notesText'):
        return jsonify({"error": "Missing 'notesText' in request payload"}), 400

    notes_to_analyze = data['notesText']
    if not isinstance(notes_to_analyze, str) or not notes_to_analyze.strip():
        return jsonify({"error": "'notesText' must be a non-empty string"}), 400

    try:
        analysis_result = analyze_notes_text(notes_to_analyze)
        return jsonify(analysis_result), 200
    except GeminiServiceError as e:
        current_app.logger.error(f"Gemini service error during notes analysis: {str(e)}")
        return jsonify({"error": "Failed to analyze notes via AI service.", "details": str(e)}), 502
    except ValueError as ve: # Catch input validation errors from the service itself
        return jsonify({"error": str(ve)}), 400
    except json.JSONDecodeError as jde: # Should be caught by GeminiServiceError in service, but as fallback
        current_app.logger.error(f"JSON decode error in notes analysis: {str(jde)}")
        return jsonify({"error": "Failed to parse AI response for notes analysis."}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in analyze notes endpoint: {str(e)}")
        return jsonify({"error": "An unexpected error occurred during notes analysis."}), 500

@ai_bp.route('/global-search', methods=['POST'])
def handle_global_search():
    data = request.get_json()
    if not data or not data.get('query'):
        return jsonify({"error": "Missing 'query' in request payload"}), 400

    search_query = data['query']
    if not isinstance(search_query, str) or not search_query.strip():
        return jsonify({"error": "'query' must be a non-empty string"}), 400

    try:
        # Fetch and serialize all context data
        # NOTE: Using .all() on relationships within serializers if they are dynamic
        # The serializers imported should ideally handle this.

        # Simplified serialization for context to pass to Gemini (matching export structure)
        # Using the export-oriented serializers from data.py would be more consistent if they were easily importable.
        # For now, re-using existing _to_json from each entity's route file.

        # Need to be careful with `researcher_to_json` if it nests all notes,
        # as the prompt asks for a separate top-level `notes` list.
        # For the context_data, we'll provide a flat list of all notes.

        # Using simplified/adapted serializers for context to avoid excessive nesting/size issues.
        # These are distinct from the ones used for direct API responses for individual entities.
        def context_researcher_to_json(r):
            return {"id": str(r.id), "name": r.name, "email": r.email, "department": r.department, "bio": r.bio or ""}

        def context_lab_to_json(l):
            return {"id": str(l.id), "name": l.name, "description": l.description or "", "principalInvestigatorId": str(l.principal_investigator_id) if l.principal_investigator_id else None}

        def context_project_to_json(p):
            return {"id": str(p.id), "name": p.name, "description": p.description or "", "leadResearcherId": str(p.pi_id) if p.pi_id else None}

        def context_compute_resource_to_json(cr):
            return {"id": str(cr.id), "name": cr.name, "type": cr.resource_type.value, "specification": cr.specification or ""}

        def context_grant_to_json(g):
            return {"id": str(g.id), "title": g.title, "agency": g.agency, "amount": g.amount, "status": g.status.value}

        def context_note_to_json(n): # For the flat list of all notes
            return {"id": str(n.id), "content": n.content or "", "researcherId": str(n.researcher_id), "projectId": str(n.project_id) if n.project_id else None}

        context_data = {
            "researchers": [context_researcher_to_json(r) for r in Researcher.query.all()],
            "labs": [context_lab_to_json(l) for l in Lab.query.all()],
            "projects": [context_project_to_json(p) for p in Project.query.all()],
            "computeResources": [context_compute_resource_to_json(cr) for cr in ComputeResource.query.all()],
            "grants": [context_grant_to_json(g) for g in Grant.query.all()],
            "notes": [context_note_to_json(n) for n in Note.query.all()] # All notes, flat list
        }

        search_results = perform_global_search(search_query, context_data)
        return jsonify(search_results), 200

    except GeminiServiceError as e:
        current_app.logger.error(f"Gemini service error during global search: {str(e)}")
        return jsonify({"error": "Failed to perform global search via AI service.", "details": str(e)}), 502
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in global search endpoint: {str(e)}")
        return jsonify({"error": "An unexpected error occurred during global search."}), 500

@ai_bp.route('/search-external-grants', methods=['POST'])
def handle_search_external_grants():
    data = request.get_json()
    if not data or not data.get('searchCriteria'):
        return jsonify({"error": "Missing 'searchCriteria' in request payload"}), 400

    search_criteria = data['searchCriteria']
    if not isinstance(search_criteria, dict):
        return jsonify({"error": "'searchCriteria' must be a dictionary"}), 400

    # Basic validation of search_criteria content (can be expanded)
    if not search_criteria.get('keywords') and not search_criteria.get('focusArea'):
        return jsonify({"error": "At least 'keywords' or 'focusArea' must be provided in searchCriteria"}), 400

    try:
        grant_results = search_external_grants_via_ai(search_criteria)
        return jsonify(grant_results), 200

    except GeminiServiceError as e:
        current_app.logger.error(f"Gemini service error during external grant search: {str(e)}")
        return jsonify({"error": "Failed to search external grants via AI service.", "details": str(e)}), 502
    except ValueError as ve: # Catches validation errors from service (e.g. bad criteria dict)
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in external grant search endpoint: {str(e)}")
        return jsonify({"error": "An unexpected error occurred during external grant search."}), 500

@ai_bp.route('/match-researchers', methods=['POST'])
def handle_match_researchers_to_grant():
    data = request.get_json()
    if not data or not data.get('grantDescription'):
        return jsonify({"error": "Missing 'grantDescription' in request payload"}), 400

    grant_description = data['grantDescription']
    if not isinstance(grant_description, str) or not grant_description.strip():
        return jsonify({"error": "'grantDescription' must be a non-empty string"}), 400

    try:
        # Fetch and serialize researcher context data
        # Using the same context serializers defined in handle_global_search for consistency
        # Ensure these local serializers are accessible or redefine them if they are not.
        # For this case, I'll assume they are accessible or can be redefined if needed.
        # The `perform_global_search` already has these; let's ensure they are available.
        # Re-defining for clarity or use from a shared context_serializers module if it existed.

        def context_researcher_to_json_for_matching(r): # Slightly different from global search one, includes bio fully
            return {
                "id": str(r.id), # Ensure ID is string for AI context consistency
                "name": r.name,
                "email": r.email, # Though AI might not need email for matching
                "department": r.department,
                "bio": r.bio or "" # Bio is crucial for matching
            }

        researchers_context = [context_researcher_to_json_for_matching(r) for r in Researcher.query.all()]

        if not researchers_context:
            return jsonify({"message": "No researchers available in the system to match.", "matches": []}), 200


        match_results = match_researchers_to_grant_via_ai(grant_description, researchers_context)
        return jsonify(match_results), 200

    except GeminiServiceError as e:
        current_app.logger.error(f"Gemini service error during researcher matching: {str(e)}")
        return jsonify({"error": "Failed to match researchers to grant via AI service.", "details": str(e)}), 502
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in researcher matching endpoint: {str(e)}")
        return jsonify({"error": "An unexpected error occurred during researcher matching."}), 500

@ai_bp.route('/generate-grant-email', methods=['POST'])
def handle_generate_grant_email():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    grant_details_payload = data.get('grant')
    pi_id_payload = data.get('piId')

    if not grant_details_payload or not isinstance(grant_details_payload, dict):
        return jsonify({"error": "Missing or invalid 'grant' details in request payload"}), 400
    if not pi_id_payload:
        return jsonify({"error": "Missing 'piId' in request payload"}), 400

    # Validate essential grant details
    if not all(k in grant_details_payload for k in ['title', 'agency', 'description']):
        return jsonify({"error": "Grant details must include 'title', 'agency', and 'description'"}), 400

    pi = Researcher.query.get(pi_id_payload)
    if not pi:
        return jsonify({"error": f"Principal Investigator with id {pi_id_payload} not found"}), 404

    # Serialize PI details for the service. Using a simplified version like context_researcher_to_json.
    # The service expects 'name', 'email', 'department', 'research' (or 'bio').
    # researcher_to_json from routes.researchers is more detailed, let's use a simpler one.
    pi_details_for_service = {
        "id": str(pi.id),
        "name": pi.name,
        "email": pi.email,
        "department": pi.department,
        "bio": pi.bio or "", # 'bio' will be used as 'research' by the service if 'research' key isn't present
        # Ensure this matches what generate_grant_intro_email_via_ai expects for pi_details
    }

    try:
        email_draft = generate_grant_intro_email_via_ai(grant_details_payload, pi_details_for_service)
        return jsonify(email_draft), 200

    except GeminiServiceError as e:
        current_app.logger.error(f"Gemini service error during email generation: {str(e)}")
        return jsonify({"error": "Failed to generate email via AI service.", "details": str(e)}), 502
    except ValueError as ve: # Catches validation errors from service (e.g. bad grant_details)
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in email generation endpoint: {str(e)}")
        return jsonify({"error": "An unexpected error occurred during email generation."}), 500
