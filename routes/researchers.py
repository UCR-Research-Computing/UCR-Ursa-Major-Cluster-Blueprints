from flask import Blueprint, request, jsonify
from models.models import Researcher, Note, Lab, Project, Grant
from app import db
from datetime import datetime, timezone # Import timezone

researcher_bp = Blueprint('researcher_bp', __name__)

# Specific Note Serializer
def note_to_json(note_obj):
    if not note_obj:
        return None
    return {
        "id": note_obj.id,
        "researcher_id": note_obj.researcher_id,
        "project_id": note_obj.project_id,
        "content": note_obj.content,
        "created_at": note_obj.created_at.isoformat() if note_obj.created_at else None,
        "updated_at": note_obj.updated_at.isoformat() if note_obj.updated_at else None
    }

def researcher_to_json(researcher_obj):
    """Serializes a Researcher object to a dictionary."""
    notes_data = [note_to_json(note) for note in researcher_obj.notes.all()] \
        if hasattr(researcher_obj.notes, 'all') else \
        [note_to_json(note) for note in researcher_obj.notes]

    led_labs_data = []
    if hasattr(researcher_obj, 'led_labs') and researcher_obj.led_labs:
        led_labs_list = researcher_obj.led_labs.all() if hasattr(researcher_obj.led_labs, 'all') else researcher_obj.led_labs
        led_labs_data = [{"id": lab.id, "name": lab.name} for lab in led_labs_list]

    member_of_lab_data = None
    if researcher_obj.lab: # If part of a lab as a member
        member_of_lab_data = {"id": researcher_obj.lab.id, "name": researcher_obj.lab.name}


    data = {
        "id": researcher_obj.id,
        "name": researcher_obj.name,
        "email": researcher_obj.email,
        "department": researcher_obj.department,
        "bio": researcher_obj.bio,
        "lab_id": researcher_obj.lab_id,
        "member_of_lab": member_of_lab_data,
        "notes": notes_data,
        "led_labs": led_labs_data
    }
    return data


@researcher_bp.route('', methods=['POST'])
def create_researcher():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    required_fields = ['name', 'email', 'department']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    if Researcher.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already exists"}), 400

    lab_id = data.get('lab_id')
    if lab_id is not None:
        if not isinstance(lab_id, int):
            return jsonify({"error": "lab_id must be an integer"}), 400
        if not Lab.query.get(lab_id):
            return jsonify({"error": f"Lab with id {lab_id} not found"}), 404

    new_researcher = Researcher(
        name=data['name'],
        email=data['email'],
        department=data['department'],
        bio=data.get('bio'),
        lab_id=lab_id
    )
    db.session.add(new_researcher)
    db.session.commit()
    return jsonify(researcher_to_json(new_researcher)), 201

@researcher_bp.route('', methods=['GET'])
def get_researchers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    researchers_page = Researcher.query.paginate(page=page, per_page=per_page, error_out=False)
    researchers_list = [researcher_to_json(researcher) for researcher in researchers_page.items]

    return jsonify({
        "researchers": researchers_list,
        "total_pages": researchers_page.pages,
        "current_page": researchers_page.page,
        "total_items": researchers_page.total
    })

@researcher_bp.route('/<int:id>', methods=['GET'])
def get_researcher(id):
    researcher = Researcher.query.get(id)
    if not researcher:
        return jsonify({"error": "Researcher not found"}), 404
    return jsonify(researcher_to_json(researcher))

@researcher_bp.route('/<int:id>', methods=['PUT'])
def update_researcher(id):
    researcher = Researcher.query.get(id)
    if not researcher:
        return jsonify({"error": "Researcher not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if 'email' in data and data['email'] != researcher.email:
        if Researcher.query.filter(Researcher.id != id, Researcher.email == data['email']).first():
            return jsonify({"error": "New email already exists"}), 400
        researcher.email = data['email']

    researcher.name = data.get('name', researcher.name)
    researcher.department = data.get('department', researcher.department)
    researcher.bio = data.get('bio', researcher.bio)

    if 'lab_id' in data:
        lab_id = data['lab_id']
        if lab_id is not None:
            if not isinstance(lab_id, int):
                return jsonify({"error": "lab_id must be an integer"}), 400
            if not Lab.query.get(lab_id):
                return jsonify({"error": f"Lab with id {lab_id} not found"}), 404
            researcher.lab_id = lab_id
        else:
            researcher.lab_id = None

    db.session.commit()
    return jsonify(researcher_to_json(researcher))

@researcher_bp.route('/<int:id>', methods=['DELETE'])
def delete_researcher(id):
    researcher = Researcher.query.get(id)
    if not researcher:
        return jsonify({"error": "Researcher not found"}), 404

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

@researcher_bp.route('/<int:researcherId>/notes', methods=['POST'])
def create_researcher_note(researcherId):
    researcher = Researcher.query.get(researcherId)
    if not researcher:
        return jsonify({"error": "Researcher not found"}), 404

    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({"error": "Missing content for note"}), 400

    project_id = data.get('projectId') # Optional: link note to a project
    if project_id:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": f"Project with id {project_id} not found"}), 404

    new_note = Note(
        researcher_id=researcherId,
        project_id=project_id, # Can be None
        content=data['content']
        # created_at and updated_at are handled by server_default and onupdate in model
    )
    db.session.add(new_note)
    db.session.commit()
    return jsonify(note_to_json(new_note)), 201

@researcher_bp.route('/<int:researcherId>/notes/<int:noteId>', methods=['PUT'])
def update_researcher_note(researcherId, noteId):
    # Fetching researcher first to ensure researcherId in path is valid, though not strictly necessary if just checking note.researcher_id
    researcher = Researcher.query.get(researcherId)
    if not researcher:
        return jsonify({"error": "Researcher not found"}), 404

    note = Note.query.get(noteId)
    if not note:
        return jsonify({"error": "Note not found"}), 404

    if note.researcher_id != researcherId:
        # This check ensures the note belongs to the researcher specified in the URL path
        return jsonify({"error": "Note does not belong to this researcher"}), 403 # 403 Forbidden

    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({"error": "Missing content for note update"}), 400

    note.content = data['content']
    note.updated_at = datetime.now(timezone.utc) # Manually update timestamp as per requirement

    # Optional: update project_id if provided
    if 'projectId' in data:
        project_id = data['projectId']
        if project_id is not None:
            project = Project.query.get(project_id)
            if not project:
                 return jsonify({"error": f"Project with id {project_id} not found"}), 404
            note.project_id = project_id
        else:
            note.project_id = None


    db.session.commit()
    return jsonify(note_to_json(note))

@researcher_bp.route('/<int:researcherId>/notes/<int:noteId>', methods=['DELETE'])
def delete_researcher_note(researcherId, noteId):
    researcher = Researcher.query.get(researcherId) # Check researcher exists
    if not researcher:
        return jsonify({"error": "Researcher not found"}), 404

    note = Note.query.get(noteId)
    if not note:
        return jsonify({"error": "Note not found"}), 404

    if note.researcher_id != researcherId:
        return jsonify({"error": "Note does not belong to this researcher"}), 403 # 403 Forbidden

    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Note deleted successfully"}), 200 # Or 204
