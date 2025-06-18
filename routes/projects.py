from flask import Blueprint, request, jsonify
from models.models import Project, Researcher, Lab, ComputeResource, Grant, Note # Added Note
from app import db
from datetime import datetime

project_bp = Blueprint('project_bp', __name__)

# Re-using mini_researcher_to_json from other route files (ideally this would be in a shared module)
def mini_researcher_to_json(researcher):
    if not researcher:
        return None
    return {
        "id": researcher.id,
        "name": researcher.name,
        "email": researcher.email,
        "department": researcher.department # Assuming Researcher model has department
    }

def mini_lab_to_json(lab):
    if not lab:
        return None
    return {
        "id": lab.id,
        "name": lab.name
    }

def mini_compute_resource_to_json(cr):
    if not cr:
        return None
    return {
        "id": cr.id,
        "name": cr.name,
        "resource_type": cr.resource_type.value # Enum value
    }

def mini_grant_to_json(grant):
    if not grant:
        return None
    return {
        "id": grant.id,
        "title": grant.title,
        "amount": grant.amount,
        "status": grant.status.value # Enum value
    }

def mini_note_to_json(note):
    if not note: return None
    return {
        "id": note.id,
        "content": note.content,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "researcher_id": note.researcher_id
    }


def project_to_json(project_obj):
    """Serializes a Project object to a dictionary."""
    # Handle dynamic relationships by calling .all() or direct access if not dynamic
    labs_list = project_obj.labs.all() if hasattr(project_obj.labs, 'all') else project_obj.labs
    compute_resources_list = project_obj.compute_resources.all() if hasattr(project_obj.compute_resources, 'all') else project_obj.compute_resources
    grants_list = project_obj.grants.all() if hasattr(project_obj.grants, 'all') else project_obj.grants
    notes_list = project_obj.notes.all() if hasattr(project_obj.notes, 'all') else project_obj.notes


    return {
        "id": project_obj.id,
        "name": project_obj.name,
        "description": project_obj.description,
        "start_date": project_obj.start_date.isoformat() if project_obj.start_date else None,
        "end_date": project_obj.end_date.isoformat() if project_obj.end_date else None,
        "principal_investigator": mini_researcher_to_json(project_obj.principal_investigator) if project_obj.principal_investigator else None,
        "labs": [mini_lab_to_json(lab) for lab in labs_list],
        "compute_resources": [mini_compute_resource_to_json(cr) for cr in compute_resources_list],
        "grants": [mini_grant_to_json(grant) for grant in grants_list],
        "notes": [mini_note_to_json(note) for note in notes_list] # Added notes
    }

@project_bp.route('', methods=['POST'])
def create_project():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    required_fields = ['name', 'description', 'startDate', 'leadResearcherId'] # leadResearcherId is pi_id
    missing_fields = [field for field in required_fields if field not in data or data[field] is None] # Check for None too
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    try:
        start_date = datetime.fromisoformat(data['startDate']) if data.get('startDate') else None
        end_date = datetime.fromisoformat(data['endDate']) if data.get('endDate') else None
    except ValueError:
        return jsonify({"error": "Invalid date format for startDate or endDate. Use ISO format."}), 400

    if not start_date: # Ensure start_date is not None after parsing
        return jsonify({"error": "startDate is required and cannot be null."}),400


    pi = Researcher.query.get(data['leadResearcherId'])
    if not pi:
        return jsonify({"error": f"Lead Researcher (PI) with id {data['leadResearcherId']} not found"}), 404

    new_project = Project(
        name=data['name'],
        description=data['description'],
        start_date=start_date,
        end_date=end_date,
        pi_id=data['leadResearcherId'] # pi_id is the foreign key field
    )

    if 'labIds' in data and data['labIds']:
        for lab_id in data['labIds']:
            lab = Lab.query.get(lab_id)
            if not lab:
                return jsonify({"error": f"Lab with id {lab_id} not found"}), 404
            new_project.labs.append(lab)

    if 'computeResourceIds' in data and data['computeResourceIds']:
        for cr_id in data['computeResourceIds']:
            cr = ComputeResource.query.get(cr_id)
            if not cr:
                return jsonify({"error": f"Compute Resource with id {cr_id} not found"}), 404
            new_project.compute_resources.append(cr)

    if 'grantIds' in data and data['grantIds']:
        for grant_id in data['grantIds']:
            grant = Grant.query.get(grant_id)
            if not grant:
                return jsonify({"error": f"Grant with id {grant_id} not found"}), 404
            new_project.grants.append(grant)

    db.session.add(new_project)
    db.session.commit()
    return jsonify(project_to_json(new_project)), 201

@project_bp.route('', methods=['GET'])
def get_projects():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    projects_page = Project.query.paginate(page=page, per_page=per_page, error_out=False)
    projects_list = [project_to_json(project) for project in projects_page.items]

    return jsonify({
        "projects": projects_list,
        "total_pages": projects_page.pages,
        "current_page": projects_page.page,
        "total_items": projects_page.total
    })

@project_bp.route('/<int:id>', methods=['GET'])
def get_project(id):
    project = Project.query.get(id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(project_to_json(project))

@project_bp.route('/<int:id>', methods=['PUT'])
def update_project(id):
    project = Project.query.get(id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    project.name = data.get('name', project.name)
    project.description = data.get('description', project.description)

    if 'startDate' in data:
        try:
            project.start_date = datetime.fromisoformat(data['startDate']) if data['startDate'] else None
        except (ValueError, TypeError): # Catch TypeError if data['startDate'] is None and fromisoformat doesn't like it
             return jsonify({"error": "Invalid date format for startDate. Use ISO format."}), 400
    if 'endDate' in data:
        try:
            project.end_date = datetime.fromisoformat(data['endDate']) if data['endDate'] else None
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid date format for endDate. Use ISO format."}), 400

    if 'leadResearcherId' in data:
        if data['leadResearcherId'] is not None:
            pi = Researcher.query.get(data['leadResearcherId'])
            if not pi:
                return jsonify({"error": f"Lead Researcher (PI) with id {data['leadResearcherId']} not found"}), 404
            project.pi_id = data['leadResearcherId']
        else: # leadResearcherId (pi_id) is not nullable
            return jsonify({"error": "leadResearcherId (pi_id) cannot be null."}), 400


    if 'labIds' in data:
        project.labs.clear()
        for lab_id in data['labIds']:
            lab = Lab.query.get(lab_id)
            if not lab:
                return jsonify({"error": f"Lab with id {lab_id} not found"}), 404
            project.labs.append(lab)

    if 'computeResourceIds' in data:
        project.compute_resources.clear()
        for cr_id in data['computeResourceIds']:
            cr = ComputeResource.query.get(cr_id)
            if not cr:
                return jsonify({"error": f"Compute Resource with id {cr_id} not found"}), 404
            project.compute_resources.append(cr)

    if 'grantIds' in data:
        project.grants.clear()
        for grant_id in data['grantIds']:
            grant = Grant.query.get(grant_id)
            if not grant:
                return jsonify({"error": f"Grant with id {grant_id} not found"}), 404
            project.grants.append(grant)

    db.session.commit()
    return jsonify(project_to_json(project))

@project_bp.route('/<int:id>', methods=['DELETE'])
def delete_project(id):
    project = Project.query.get(id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # Many-to-many relationships (labs, compute_resources, grants)
    # are typically handled by SQLAlchemy's session management when the parent
    # object (project) is deleted, or by cascade options if defined on the model.
    # Clearing them explicitly ensures association table entries are removed if no cascade delete-orphan.
    project.labs.clear()
    project.compute_resources.clear()
    project.grants.clear()

    # One-to-many for notes: if Project.notes has cascade="all, delete-orphan"
    # notes will be deleted. Otherwise, they need to be handled (e.g. set project_id to null or delete).
    # Current Note model has project_id nullable=True.
    # If we want to delete notes associated with the project:
    Note.query.filter_by(project_id=id).delete(synchronize_session='fetch')


    db.session.delete(project)
    db.session.commit()

    return jsonify({"message": "Project and associated notes deleted successfully"}), 200 # Or 204
