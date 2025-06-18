from flask import Blueprint, request, jsonify
from models.models import Lab, Researcher, Project
from app import db
from schemas import LabSchema # Import LabSchema
from marshmallow import ValidationError

lab_bp = Blueprint('lab_bp', __name__)

# Instantiate schemas
lab_schema = LabSchema()
labs_schema = LabSchema(many=True)
# For updates, we'll use lab_schema with partial=True: LabSchema(partial=True)

@lab_bp.route('', methods=['POST'])
def create_lab():
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No input data provided"}), 400

    try:
        # Schema will load basic fields. Relationships from IDs need manual handling.
        # The schema has principal_investigator_id and project_ids as load_only fields.
        loaded_data = lab_schema.load(json_data) # load_instance=True creates a Lab object

        new_lab = loaded_data # This is the Lab instance if load_instance=True

        # Handle relationships based on IDs passed in json_data, not directly via schema for complex linking
        if 'principalInvestigatorId' in json_data and json_data['principalInvestigatorId'] is not None:
            pi = Researcher.query.get(json_data['principalInvestigatorId'])
            if not pi:
                return jsonify({"error": f"Principal Investigator with id {json_data['principalInvestigatorId']} not found"}), 404
            new_lab.principal_investigator = pi # Assign the object
            new_lab.principal_investigator_id = pi.id # Ensure FK is set if not done by relationship assignment
        else:
            new_lab.principal_investigator_id = None # Explicitly nullify if not provided or null
            new_lab.principal_investigator = None


        if 'projectIds' in json_data and json_data['projectIds']:
            new_lab.projects.clear() # Clear existing before adding new ones, if any
            for project_id in json_data['projectIds']:
                project = Project.query.get(project_id)
                if not project:
                    return jsonify({"error": f"Project with id {project_id} not found"}), 404
                new_lab.projects.append(project)

        db.session.add(new_lab) # Add the instance if schema didn't auto-add via session
        db.session.commit()
        return jsonify(lab_schema.dump(new_lab)), 201
    except ValidationError as err:
        return jsonify(err.messages), 400

@lab_bp.route('', methods=['GET'])
def get_labs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    labs_page = Lab.query.paginate(page=page, per_page=per_page, error_out=False)
    result = labs_schema.dump(labs_page.items)

    return jsonify({
        "labs": result,
        "total_pages": labs_page.pages,
        "current_page": labs_page.page,
        "total_items": labs_page.total
    })

@lab_bp.route('/<int:id>', methods=['GET'])
def get_lab(id):
    lab = Lab.query.get_or_404(id)
    return jsonify(lab_schema.dump(lab))

@lab_bp.route('/<int:id>', methods=['PUT'])
def update_lab(id):
    lab_instance = Lab.query.get_or_404(id)
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Use partial=True for updates. load_instance=True updates lab_instance directly.
        # Schema handles basic field updates. Relationships from IDs need careful handling.
        # The schema has principal_investigator_id and project_ids as load_only.
        # These won't be directly applied to model by schema.load if they are not model attributes.
        # We need to handle them manually *after* schema.load validates other fields.

        # Load basic attributes onto the instance
        lab_schema.load(json_data, instance=lab_instance, partial=True)

        # Manual handling for relationships based on IDs from json_data
        if 'principalInvestigatorId' in json_data:
            pi_id = json_data['principalInvestigatorId']
            if pi_id is not None:
                pi = Researcher.query.get(pi_id)
                if not pi:
                    return jsonify({"error": f"Principal Investigator with id {pi_id} not found"}), 404
                lab_instance.principal_investigator = pi
                lab_instance.principal_investigator_id = pi.id
            else: # Allow unsetting PI
                lab_instance.principal_investigator = None
                lab_instance.principal_investigator_id = None

        if 'projectIds' in json_data:
            lab_instance.projects.clear() # Clear existing before adding new ones
            for project_id in json_data['projectIds']:
                project = Project.query.get(project_id)
                if not project:
                    return jsonify({"error": f"Project with id {project_id} not found"}), 404
                lab_instance.projects.append(project)

        db.session.commit()
        return jsonify(lab_schema.dump(lab_instance))
    except ValidationError as err:
        return jsonify(err.messages), 400


@lab_bp.route('/<int:id>', methods=['DELETE'])
def delete_lab(id): # No schema validation needed for delete
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
