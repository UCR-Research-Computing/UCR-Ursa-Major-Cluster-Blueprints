from flask import Blueprint, request, jsonify
from models.models import Grant, Researcher, Project # GrantStatus enum is handled by schema
from app import db
from schemas import GrantSchema # Import GrantSchema
from marshmallow import ValidationError
# Removed datetime import as schema handles date parsing/validation

grant_bp = Blueprint('grant_bp', __name__)

# Instantiate schemas
grant_schema = GrantSchema()
grants_schema = GrantSchema(many=True)
# For updates, use grant_schema(partial=True)

@grant_bp.route('', methods=['POST'])
def create_grant():
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No input data provided"}), 400

    try:
        # Schema handles loading basic fields, enum validation, date parsing, and data_key mapping
        # load_instance=True creates a Grant instance
        new_grant = grant_schema.load(json_data)

        # Manual validation and linking for relationships (PI already set by schema due to pi_id field)
        if not Researcher.query.get(new_grant.pi_id): # pi_id comes from principalInvestigatorId
             # This check is somewhat redundant if FK constraints are active and schema requires pi_id
            return jsonify({"error": f"Principal Investigator with id {new_grant.pi_id} not found"}), 404

        if 'coPiIds' in json_data and json_data['coPiIds']:
            new_grant.co_pis.clear()
            for co_pi_id in json_data['coPiIds']:
                co_pi = Researcher.query.get(co_pi_id)
                if not co_pi:
                    return jsonify({"error": f"Co-PI Researcher with id {co_pi_id} not found"}), 404
                new_grant.co_pis.append(co_pi)

        if 'projectIds' in json_data and json_data['projectIds']:
            new_grant.projects.clear()
            for project_id in json_data['projectIds']:
                project = Project.query.get(project_id)
                if not project:
                    return jsonify({"error": f"Project with id {project_id} not found"}), 404
                new_grant.projects.append(project)

        # db.session.add(new_grant) # Not needed if load_instance=True and session is bound
        db.session.commit()
        return jsonify(grant_schema.dump(new_grant)), 201
    except ValidationError as err:
        return jsonify(err.messages), 400

@grant_bp.route('', methods=['GET'])
def get_grants():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    grants_page = Grant.query.paginate(page=page, per_page=per_page, error_out=False)
    result = grants_schema.dump(grants_page.items)

    return jsonify({
        "grants": result,
        "total_pages": grants_page.pages,
        "current_page": grants_page.page,
        "total_items": grants_page.total
    })

@grant_bp.route('/<int:id>', methods=['GET'])
def get_grant(id):
    grant = Grant.query.get_or_404(id)
    return jsonify(grant_schema.dump(grant))

@grant_bp.route('/<int:id>', methods=['PUT'])
def update_grant(id):
    grant_instance = Grant.query.get_or_404(id)
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # load_instance=True updates grant_instance directly
        # Schema handles basic fields, enum validation, date parsing, and data_key mapping for pi_id
        updated_grant = grant_schema.load(json_data, instance=grant_instance, partial=True)

        # Manual validation for PI if changed
        if 'principalInvestigatorId' in json_data: # Check original key
            if updated_grant.pi_id is None: # pi_id is not nullable on model
                 return jsonify({"error": "principalInvestigatorId (pi_id) cannot be null."}), 400
            if not Researcher.query.get(updated_grant.pi_id):
                return jsonify({"error": f"Principal Investigator with id {updated_grant.pi_id} not found"}), 404

        # Manual handling for M2M relationships based on IDs from json_data
        if 'coPiIds' in json_data:
            updated_grant.co_pis.clear()
            for co_pi_id in json_data['coPiIds']:
                co_pi = Researcher.query.get(co_pi_id)
                if not co_pi:
                    return jsonify({"error": f"Co-PI Researcher with id {co_pi_id} not found"}), 404
                updated_grant.co_pis.append(co_pi)

        if 'projectIds' in json_data:
            updated_grant.projects.clear()
            for project_id in json_data['projectIds']:
                project = Project.query.get(project_id)
                if not project:
                    return jsonify({"error": f"Project with id {project_id} not found"}), 404
                updated_grant.projects.append(project)

        db.session.commit()
        return jsonify(grant_schema.dump(updated_grant))
    except ValidationError as err:
        return jsonify(err.messages), 400

@grant_bp.route('/<int:id>', methods=['DELETE'])
def delete_grant(id): # No schema validation needed for delete
    grant = Grant.query.get(id)
    if not grant:
        return jsonify({"error": "Grant not found"}), 404

    grant.co_pis.clear()
    grant.projects.clear()

    db.session.delete(grant)
    db.session.commit()

    return jsonify({"message": "Grant deleted successfully"}), 200
