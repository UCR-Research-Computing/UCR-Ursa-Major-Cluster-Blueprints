from flask import Blueprint, request, jsonify
from models.models import Lab, Researcher, Project # Import necessary models
from app import db # Import db instance

lab_bp = Blueprint('lab_bp', __name__)

# Basic serialization for related objects (can be expanded)
def mini_researcher_to_json(researcher):
    if not researcher:
        return None
    return {
        "id": researcher.id,
        "name": researcher.name,
        "email": researcher.email,
        "department": researcher.department
    }

def mini_project_to_json(project):
    if not project:
        return None
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description
    }

def lab_to_json(lab_obj):
    """Serializes a Lab object to a dictionary."""
    projects_data = []
    if lab_obj.projects: # lab.projects is dynamic (or subquery)
        # If it's dynamic, use .all(), otherwise, it's already a list
        projects_list = lab_obj.projects.all() if hasattr(lab_obj.projects, 'all') else lab_obj.projects
        projects_data = [mini_project_to_json(p) for p in projects_list]

    return {
        "id": lab_obj.id,
        "name": lab_obj.name,
        "description": lab_obj.description,
        "principal_investigator": mini_researcher_to_json(lab_obj.principal_investigator) if lab_obj.principal_investigator else None,
        "members": [mini_researcher_to_json(member) for member in lab_obj.members.all()] if hasattr(lab_obj.members, 'all') else [], # Assuming lab.members is dynamic
        "projects": projects_data
    }

@lab_bp.route('', methods=['POST'])
def create_lab():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    required_fields = ['name', 'description']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    new_lab = Lab(
        name=data['name'],
        description=data['description']
    )

    if 'principalInvestigatorId' in data and data['principalInvestigatorId'] is not None:
        pi = Researcher.query.get(data['principalInvestigatorId'])
        if not pi:
            return jsonify({"error": f"Principal Investigator with id {data['principalInvestigatorId']} not found"}), 404
        new_lab.principal_investigator = pi

    if 'projectIds' in data and data['projectIds']:
        projects = []
        for project_id in data['projectIds']:
            project = Project.query.get(project_id)
            if not project:
                return jsonify({"error": f"Project with id {project_id} not found"}), 404
            projects.append(project)
        new_lab.projects = projects # Assign list of Project objects

    db.session.add(new_lab)
    db.session.commit()
    return jsonify(lab_to_json(new_lab)), 201

@lab_bp.route('', methods=['GET'])
def get_labs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    labs_page = Lab.query.paginate(page=page, per_page=per_page, error_out=False)
    labs_list = [lab_to_json(lab) for lab in labs_page.items]

    return jsonify({
        "labs": labs_list,
        "total_pages": labs_page.pages,
        "current_page": labs_page.page,
        "total_items": labs_page.total
    })

@lab_bp.route('/<int:id>', methods=['GET'])
def get_lab(id):
    lab = Lab.query.get(id)
    if not lab:
        return jsonify({"error": "Lab not found"}), 404
    return jsonify(lab_to_json(lab))

@lab_bp.route('/<int:id>', methods=['PUT'])
def update_lab(id):
    lab = Lab.query.get(id)
    if not lab:
        return jsonify({"error": "Lab not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    lab.name = data.get('name', lab.name)
    lab.description = data.get('description', lab.description)

    if 'principalInvestigatorId' in data:
        pi_id = data['principalInvestigatorId']
        if pi_id is not None:
            pi = Researcher.query.get(pi_id)
            if not pi:
                return jsonify({"error": f"Principal Investigator with id {pi_id} not found"}), 404
            lab.principal_investigator = pi
        else: # Allow unsetting PI
            lab.principal_investigator = None
            lab.principal_investigator_id = None


    if 'projectIds' in data:
        projects = []
        if data['projectIds']: # If empty list provided, it will clear projects
            for project_id in data['projectIds']:
                project = Project.query.get(project_id)
                if not project:
                    return jsonify({"error": f"Project with id {project_id} not found"}), 404
                projects.append(project)
        lab.projects = projects # Reassign the list of projects

    db.session.commit()
    return jsonify(lab_to_json(lab))

@lab_bp.route('/<int:id>', methods=['DELETE'])
def delete_lab(id):
    lab = Lab.query.get(id)
    if not lab:
        return jsonify({"error": "Lab not found"}), 404

    # Update Researcher records: set lab_id to None for members of this lab
    # Lab.members is a dynamic relationship
    for member in lab.members.all(): # Use .all() for dynamic relationship
        member.lab_id = None
        # member.lab = None # Also works

    # Update Project records: remove this lab from projects' lab lists
    # Lab.projects is a list of Project objects.
    # The relationship is many-to-many via project_labs_table.
    # SQLAlchemy handles removing associations from the association table
    # when a many-to-many collection is cleared or an object is removed from it.
    # Here, we are deleting the lab, so associations in project_labs should be removed.
    # If cascade="all, delete-orphan" is set on Project.labs or Lab.projects, it might handle this.
    # Otherwise, explicit removal from the association table is needed or by clearing collections.
    # Since we are deleting the lab, we expect the ORM to handle entries in `project_labs_table`.
    # If `lab.projects` is `lazy='subquery'`, it's a list. If `lazy='dynamic'`, it's a query.
    # Lab.projects is currently `lazy='dynamic'` from models/models.py after reset.
    # Clearing the collection before deleting the lab ensures associations are removed.
    lab.projects.clear()


    db.session.delete(lab)
    db.session.commit()

    return jsonify({"message": "Lab deleted successfully"}), 200 # Or 204 (No Content)
