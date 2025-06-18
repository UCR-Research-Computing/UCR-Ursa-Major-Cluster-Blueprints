from flask import Blueprint, request, jsonify
from models.models import Researcher, Note, Lab, Project, Grant
from app import db
from datetime import datetime, timezone # Import timezone
from schemas import ResearcherSchema, NoteSchema, ResearcherUpdateSchema # Import schemas
from marshmallow import ValidationError # For explicit error handling if not using app.errorhandler

researcher_bp = Blueprint('researcher_bp', __name__)

# Instantiate schemas
researcher_schema = ResearcherSchema()
researchers_schema = ResearcherSchema(many=True) # For lists of researchers
researcher_update_schema = ResearcherUpdateSchema()
note_schema = NoteSchema() # For single note responses
# notes_schema = NoteSchema(many=True) # If ever needed for lists of notes standalone

@researcher_bp.route('', methods=['POST'])
def create_researcher():
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No input data provided"}), 400

    try:
        # Validate and deserialize request data to a Researcher object
        new_researcher = researcher_schema.load(json_data)

        # Check for existing email (Marshmallow doesn't do unique checks against DB by default)
        if Researcher.query.filter_by(email=new_researcher.email).first():
            return jsonify({"error": "Email already exists"}), 400

        # Optional: Validate lab_id if provided and not handled by schema's FK validation fully
        if new_researcher.lab_id is not None:
            if not Lab.query.get(new_researcher.lab_id):
                 return jsonify({"error": f"Lab with id {new_researcher.lab_id} not found"}), 404

        db.session.add(new_researcher)
        db.session.commit()
        # Serialize the new researcher object for the response
        return jsonify(researcher_schema.dump(new_researcher)), 201
    except ValidationError as err:
        return jsonify(err.messages), 400


@researcher_bp.route('', methods=['GET'])
def get_researchers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    researchers_page = Researcher.query.paginate(page=page, per_page=per_page, error_out=False)
    # Serialize the list of researcher objects
    result = researchers_schema.dump(researchers_page.items)

    return jsonify({
        "researchers": result,
        "total_pages": researchers_page.pages,
        "current_page": researchers_page.page,
        "total_items": researchers_page.total
    })

@researcher_bp.route('/<int:id>', methods=['GET'])
def get_researcher(id):
    researcher = Researcher.query.get_or_404(id) # Use get_or_404 for convenience
    # Serialize the researcher object
    return jsonify(researcher_schema.dump(researcher))

@researcher_bp.route('/<int:id>', methods=['PUT'])
def update_researcher(id):
    researcher = Researcher.query.get_or_404(id)
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No input data provided"}), 400

    try:
        # Validate and deserialize request data, updating the existing researcher instance
        # Pass partial=True to allow partial updates
        updated_researcher = researcher_update_schema.load(json_data, instance=researcher, partial=True)

        # If email is being changed, check for uniqueness
        if 'email' in json_data and json_data['email'] != researcher.email: # Check if email key is in payload
             if Researcher.query.filter(Researcher.email == updated_researcher.email, Researcher.id != id).first():
                return jsonify({"error": "New email already exists"}), 400

        # Optional: Validate lab_id if provided and not handled by schema's FK validation fully
        if updated_researcher.lab_id is not None: # Check the attribute on the updated instance
            if not Lab.query.get(updated_researcher.lab_id):
                 return jsonify({"error": f"Lab with id {updated_researcher.lab_id} not found"}), 404

        db.session.commit()
        # Serialize the updated researcher object for the response
        return jsonify(researcher_schema.dump(updated_researcher))
    except ValidationError as err:
        return jsonify(err.messages), 400

@researcher_bp.route('/<int:id>', methods=['DELETE'])
def delete_researcher(id): # Keep existing delete logic, no schema validation needed for delete
    researcher = Researcher.query.get_or_404(id) # Using get_or_404

    # Existing logic for checking dependencies before deleting
    if Project.query.filter_by(pi_id=id).first():
        return jsonify({"error": "Researcher is PI on one or more Projects. Reassign PI before deleting."}), 400
    if Grant.query.filter_by(pi_id=id).first():
        return jsonify({"error": "Researcher is PI on one or more Grants. Reassign PI before deleting."}), 400

    labs_led = Lab.query.filter_by(principal_investigator_id=id).all()
    for lab in labs_led:
        lab.principal_investigator_id = None

    for grant_obj in list(researcher.grants_co_pi):
        grant_obj.co_pis.remove(researcher)

    Note.query.filter_by(researcher_id=id).delete(synchronize_session='fetch')

    db.session.delete(researcher)
    db.session.commit()

    return jsonify({"message": "Researcher deleted successfully"}), 200

# --- Notes specific routes ---
# These will also be updated to use NoteSchema for request validation and response serialization

@researcher_bp.route('/<int:researcherId>/notes', methods=['POST'])
def create_researcher_note(researcherId):
    researcher = Researcher.query.get_or_404(researcherId) # Ensure researcher exists

    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No input data provided"}), 400

    try:
        # We need to ensure researcherId from path is used, not from payload (if any)
        # And that projectId if present in payload is handled.
        # NoteSchema will expect 'researcher_id' and 'project_id' if they are part of its fields.
        # For creating, it's better to pass these explicitly to the model.

        if not json_data.get('content'):
             return jsonify({"error": "Missing content for note"}), 400

        project_id_payload = json_data.get('projectId')
        project_instance = None
        if project_id_payload is not None:
            project_instance = Project.query.get(project_id_payload)
            if not project_instance:
                return jsonify({"error": f"Project with id {project_id_payload} not found"}), 404

        # Create Note instance directly, not through schema.load if path params are involved for FKs
        new_note = Note(
            researcher_id=researcherId,
            project_id=project_instance.id if project_instance else None,
            content=json_data['content']
        )
        db.session.add(new_note)
        db.session.commit()
        return jsonify(note_schema.dump(new_note)), 201
    except ValidationError as err: # Though manual validation is done above for content
        return jsonify(err.messages), 400


@researcher_bp.route('/<int:researcherId>/notes/<int:noteId>', methods=['PUT'])
def update_researcher_note(researcherId, noteId):
    Researcher.query.get_or_404(researcherId) # Ensure researcher exists
    note = Note.query.filter_by(id=noteId, researcher_id=researcherId).first_or_404() # Ensure note exists and belongs to researcher

    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No input data provided"}), 400

    # Using partial=True to allow partial updates for content or project_id
    # NoteSchema by default would require all its fields if not partial.
    # However, for simple note update, just content and maybe project_id.

    if 'content' not in json_data or not json_data['content']: # Content is required for update
        return jsonify({"error": "Content cannot be empty for note update"}), 400

    note.content = json_data['content']
    note.updated_at = datetime.now(timezone.utc)

    if 'projectId' in json_data:
        project_id_payload = json_data['projectId']
        if project_id_payload is not None:
            project_instance = Project.query.get(project_id_payload)
            if not project_instance:
                return jsonify({"error": f"Project with id {project_id_payload} not found"}), 404
            note.project_id = project_instance.id
        else:
            note.project_id = None # Allow unlinking project from note

    db.session.commit()
    return jsonify(note_schema.dump(note))

@researcher_bp.route('/<int:researcherId>/notes/<int:noteId>', methods=['DELETE'])
def delete_researcher_note(researcherId, noteId):
    Researcher.query.get_or_404(researcherId) # Ensure researcher exists
    note = Note.query.filter_by(id=noteId, researcher_id=researcherId).first_or_404()

    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Note deleted successfully"}), 200
