from flask import Blueprint, request, jsonify
from models.models import ComputeResource, Project # Enums are handled by schema
from app import db
from schemas import ComputeResourceSchema # Import schema
from marshmallow import ValidationError

compute_resource_bp = Blueprint('compute_resource_bp', __name__)

# Instantiate schemas
compute_resource_schema = ComputeResourceSchema()
compute_resources_schema = ComputeResourceSchema(many=True)
# For updates, use compute_resource_schema(partial=True)

@compute_resource_bp.route('', methods=['POST'])
def create_compute_resource():
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No input data provided"}), 400

    try:
        # Schema handles loading basic fields, enum validation, and data_key mapping
        # load_instance=True creates a ComputeResource instance
        new_cr = compute_resource_schema.load(json_data)

        # Manual handling for 'project_ids' relationship
        if 'projectIds' in json_data and json_data['projectIds']:
            new_cr.projects.clear() # Should be empty for new instance, but good practice
            for project_id in json_data['projectIds']:
                project = Project.query.get(project_id)
                if not project:
                    # No rollback here as instance not yet added to session by us
                    return jsonify({"error": f"Project with id {project_id} not found"}), 404
                new_cr.projects.append(project)

        db.session.add(new_cr) # Add if schema doesn't auto-add
        db.session.commit()
        return jsonify(compute_resource_schema.dump(new_cr)), 201
    except ValidationError as err:
        return jsonify(err.messages), 400

@compute_resource_bp.route('', methods=['GET'])
def get_compute_resources():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    resources_page = ComputeResource.query.paginate(page=page, per_page=per_page, error_out=False)
    result = compute_resources_schema.dump(resources_page.items)

    return jsonify({
        "compute_resources": result,
        "total_pages": resources_page.pages,
        "current_page": resources_page.page,
        "total_items": resources_page.total
    })

@compute_resource_bp.route('/<int:id>', methods=['GET'])
def get_compute_resource(id):
    cr = ComputeResource.query.get_or_404(id)
    return jsonify(compute_resource_schema.dump(cr))

@compute_resource_bp.route('/<int:id>', methods=['PUT'])
def update_compute_resource(id):
    cr_instance = ComputeResource.query.get_or_404(id)
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # load_instance=True updates cr_instance directly
        # Schema handles basic fields, enum validation, and data_key mapping
        updated_cr = compute_resource_schema.load(json_data, instance=cr_instance, partial=True)

        # Manual handling for 'project_ids' relationship
        if 'projectIds' in json_data:
            updated_cr.projects.clear()
            for project_id in json_data['projectIds']:
                project = Project.query.get(project_id)
                if not project:
                    return jsonify({"error": f"Project with id {project_id} not found"}), 404
                updated_cr.projects.append(project)

        db.session.commit()
        return jsonify(compute_resource_schema.dump(updated_cr))
    except ValidationError as err:
        return jsonify(err.messages), 400

@compute_resource_bp.route('/<int:id>', methods=['DELETE'])
def delete_compute_resource(id): # No schema validation needed for delete
    cr = ComputeResource.query.get(id)
    if not cr:
        return jsonify({"error": "Compute Resource not found"}), 404

    # Many-to-many relationship with Project
    cr.projects.clear() # Remove associations from project_compute_resources table

    db.session.delete(cr)
    db.session.commit()

    return jsonify({"message": "Compute Resource deleted successfully"}), 200
