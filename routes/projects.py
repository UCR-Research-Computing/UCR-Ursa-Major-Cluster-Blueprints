from flask import Blueprint, request, jsonify
from models.models import Project, Researcher, Lab, ComputeResource, Grant, Note
from app import db
from schemas import ProjectSchema # Import ProjectSchema
from marshmallow import ValidationError
from datetime import datetime # Keep for manual date parsing if needed, though schema handles it

project_bp = Blueprint('project_bp', __name__)

# Instantiate schemas
project_schema = ProjectSchema()
projects_schema = ProjectSchema(many=True)
# For updates, use project_schema(partial=True) or define ProjectUpdateSchema

@project_bp.route('', methods=['POST'])
def create_project():
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No input data provided"}), 400

    try:
        # Schema handles loading basic fields and `data_key` mapping for IDs
        # `load_instance=True` creates a Project instance
        new_project = project_schema.load(json_data)

        # Manual validation and linking for relationships based on IDs
        # `pi_id` is already set by schema due to `load_instance=True` and direct model field mapping.
        # Check existence of PI (though FK constraint would catch it too, better to be explicit)
        if not Researcher.query.get(new_project.pi_id):
            return jsonify({"error": f"Lead Researcher (PI) with id {new_project.pi_id} not found"}), 404

        if 'labIds' in json_data and json_data['labIds']:
            new_project.labs.clear()
            for lab_id in json_data['labIds']: # Use original json_data for IDs
                lab = Lab.query.get(lab_id)
                if not lab:
                    return jsonify({"error": f"Lab with id {lab_id} not found"}), 404
                new_project.labs.append(lab)

        if 'computeResourceIds' in json_data and json_data['computeResourceIds']:
            new_project.compute_resources.clear()
            for cr_id in json_data['computeResourceIds']:
                cr = ComputeResource.query.get(cr_id)
                if not cr:
                    return jsonify({"error": f"Compute Resource with id {cr_id} not found"}), 404
                new_project.compute_resources.append(cr)

        if 'grantIds' in json_data and json_data['grantIds']:
            new_project.grants.clear()
            for grant_id in json_data['grantIds']:
                grant = Grant.query.get(grant_id)
                if not grant:
                    return jsonify({"error": f"Grant with id {grant_id} not found"}), 404
                new_project.grants.append(grant)

        # If not using load_instance=True or if session needs to be aware:
        # db.session.add(new_project)
        db.session.commit()
        return jsonify(project_schema.dump(new_project)), 201
    except ValidationError as err:
        return jsonify(err.messages), 400

@project_bp.route('', methods=['GET'])
def get_projects():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    projects_page = Project.query.paginate(page=page, per_page=per_page, error_out=False)
    result = projects_schema.dump(projects_page.items)

    return jsonify({
        "projects": result,
        "total_pages": projects_page.pages,
        "current_page": projects_page.page,
        "total_items": projects_page.total
    })

@project_bp.route('/<int:id>', methods=['GET'])
def get_project(id):
    project = Project.query.get_or_404(id)
    return jsonify(project_schema.dump(project))

@project_bp.route('/<int:id>', methods=['PUT'])
def update_project(id):
    project_instance = Project.query.get_or_404(id)
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Use partial=True for updates. Updates project_instance directly.
        # Schema handles basic fields and `data_key` mapping for `pi_id`.
        updated_project = project_schema.load(json_data, instance=project_instance, partial=True)

        # Manual handling for relationship updates based on IDs from json_data
        # Check existence of PI if pi_id was in json_data and changed
        if 'leadResearcherId' in json_data: # Check original key from payload
            if updated_project.pi_id is None: # pi_id is not nullable on model
                 return jsonify({"error": "leadResearcherId (pi_id) cannot be null."}), 400
            if not Researcher.query.get(updated_project.pi_id):
                return jsonify({"error": f"Lead Researcher (PI) with id {updated_project.pi_id} not found"}), 404

        if 'labIds' in json_data:
            updated_project.labs.clear()
            for lab_id in json_data['labIds']:
                lab = Lab.query.get(lab_id)
                if not lab:
                    return jsonify({"error": f"Lab with id {lab_id} not found"}), 404
                updated_project.labs.append(lab)

        if 'computeResourceIds' in json_data:
            updated_project.compute_resources.clear()
            for cr_id in json_data['computeResourceIds']:
                cr = ComputeResource.query.get(cr_id)
                if not cr:
                    return jsonify({"error": f"Compute Resource with id {cr_id} not found"}), 404
                updated_project.compute_resources.append(cr)

        if 'grantIds' in json_data:
            updated_project.grants.clear()
            for grant_id in json_data['grantIds']:
                grant = Grant.query.get(grant_id)
                if not grant:
                    return jsonify({"error": f"Grant with id {grant_id} not found"}), 404
                updated_project.grants.append(grant)

        db.session.commit()
        return jsonify(project_schema.dump(updated_project))
    except ValidationError as err:
        return jsonify(err.messages), 400

@project_bp.route('/<int:id>', methods=['DELETE'])
def delete_project(id): # No schema validation needed for delete
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
