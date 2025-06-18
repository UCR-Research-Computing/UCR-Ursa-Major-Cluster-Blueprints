from flask import Blueprint, request, jsonify
from models.models import Grant, Researcher, Project, GrantStatus # Enum
from app import db
from datetime import datetime

grant_bp = Blueprint('grant_bp', __name__)

# Mini serializers (ideally shared)
def mini_researcher_to_json(researcher):
    if not researcher: return None
    return {"id": researcher.id, "name": researcher.name, "email": researcher.email}

def mini_project_to_json(project):
    if not project: return None
    return {"id": project.id, "name": project.name}

def grant_to_json(grant_obj):
    """Serializes a Grant object to a dictionary."""
    # Handle dynamic relationships by calling .all()
    co_pis_list = grant_obj.co_pis.all() if hasattr(grant_obj.co_pis, 'all') else grant_obj.co_pis
    projects_list = grant_obj.projects.all() if hasattr(grant_obj.projects, 'all') else grant_obj.projects

    return {
        "id": grant_obj.id,
        "title": grant_obj.title,
        "description": grant_obj.description,
        "agency": grant_obj.agency,
        "grant_number": grant_obj.grant_number,
        "amount": grant_obj.amount,
        "status": grant_obj.status.value, # Enum value
        "proposal_due_date": grant_obj.proposal_due_date.isoformat() if grant_obj.proposal_due_date else None,
        "award_date": grant_obj.award_date.isoformat() if grant_obj.award_date else None,
        "start_date": grant_obj.start_date.isoformat() if grant_obj.start_date else None,
        "end_date": grant_obj.end_date.isoformat() if grant_obj.end_date else None,
        "principal_investigator": mini_researcher_to_json(grant_obj.principal_investigator) if grant_obj.principal_investigator else None,
        "co_pis": [mini_researcher_to_json(pi) for pi in co_pis_list],
        "projects": [mini_project_to_json(p) for p in projects_list]
    }

def parse_date(date_string):
    if not date_string:
        return None
    try:
        return datetime.fromisoformat(date_string)
    except ValueError:
        return "invalid_date" # Sentinel to indicate parsing error

@grant_bp.route('', methods=['POST'])
def create_grant():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    required_fields = ['title', 'agency', 'principalInvestigatorId', 'amount', 'startDate', 'endDate', 'status']
    missing_fields = [field for field in required_fields if data.get(field) is None] # Check for None explicitly
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    # Date parsing
    start_date = parse_date(data.get('startDate'))
    end_date = parse_date(data.get('endDate'))
    proposal_due_date = parse_date(data.get('proposalDueDate'))
    award_date = parse_date(data.get('awardDate'))

    if any(d == "invalid_date" for d in [start_date, end_date, proposal_due_date, award_date]):
        return jsonify({"error": "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD)."}), 400

    if not start_date or not end_date: # Ensure required dates are not None after parsing attempt
         return jsonify({"error": "startDate and endDate are required."}), 400


    try:
        status_enum = GrantStatus(data['status'])
    except ValueError:
        valid_statuses = [e.value for e in GrantStatus]
        return jsonify({"error": f"Invalid status '{data['status']}'. Must be one of {valid_statuses}"}), 400

    pi = Researcher.query.get(data['principalInvestigatorId'])
    if not pi:
        return jsonify({"error": f"Principal Investigator with id {data['principalInvestigatorId']} not found"}), 404

    new_grant = Grant(
        title=data['title'],
        agency=data['agency'],
        grant_number=data.get('grantNumber'),
        description=data.get('description'),
        amount=data['amount'],
        status=status_enum,
        proposal_due_date=proposal_due_date,
        award_date=award_date,
        start_date=start_date,
        end_date=end_date,
        pi_id=data['principalInvestigatorId']
    )

    if 'coPiIds' in data and data['coPiIds']:
        for co_pi_id in data['coPiIds']:
            co_pi = Researcher.query.get(co_pi_id)
            if not co_pi:
                return jsonify({"error": f"Co-PI Researcher with id {co_pi_id} not found"}), 404
            new_grant.co_pis.append(co_pi)

    if 'projectIds' in data and data['projectIds']:
        for project_id in data['projectIds']:
            project = Project.query.get(project_id)
            if not project:
                return jsonify({"error": f"Project with id {project_id} not found"}), 404
            new_grant.projects.append(project)

    db.session.add(new_grant)
    db.session.commit()
    return jsonify(grant_to_json(new_grant)), 201

@grant_bp.route('', methods=['GET'])
def get_grants():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    grants_page = Grant.query.paginate(page=page, per_page=per_page, error_out=False)
    grants_list = [grant_to_json(grant) for grant in grants_page.items]

    return jsonify({
        "grants": grants_list,
        "total_pages": grants_page.pages,
        "current_page": grants_page.page,
        "total_items": grants_page.total
    })

@grant_bp.route('/<int:id>', methods=['GET'])
def get_grant(id):
    grant = Grant.query.get(id)
    if not grant:
        return jsonify({"error": "Grant not found"}), 404
    return jsonify(grant_to_json(grant))

@grant_bp.route('/<int:id>', methods=['PUT'])
def update_grant(id):
    grant = Grant.query.get(id)
    if not grant:
        return jsonify({"error": "Grant not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    grant.title = data.get('title', grant.title)
    grant.agency = data.get('agency', grant.agency)
    grant.grant_number = data.get('grantNumber', grant.grant_number)
    grant.description = data.get('description', grant.description)
    grant.amount = data.get('amount', grant.amount)

    if 'status' in data:
        try:
            grant.status = GrantStatus(data['status'])
        except ValueError:
            valid_statuses = [e.value for e in GrantStatus]
            return jsonify({"error": f"Invalid status '{data['status']}'. Must be one of {valid_statuses}"}), 400

    # Date updates
    for date_field_key, date_attr_name in [
        ('proposalDueDate', 'proposal_due_date'),
        ('awardDate', 'award_date'),
        ('startDate', 'start_date'),
        ('endDate', 'end_date')
    ]:
        if date_field_key in data:
            parsed_date = parse_date(data[date_field_key])
            if parsed_date == "invalid_date":
                return jsonify({"error": f"Invalid date format for {date_field_key}. Use ISO format."}), 400
            setattr(grant, date_attr_name, parsed_date)

    if 'principalInvestigatorId' in data:
        if data['principalInvestigatorId'] is not None:
            pi = Researcher.query.get(data['principalInvestigatorId'])
            if not pi:
                return jsonify({"error": f"Principal Investigator with id {data['principalInvestigatorId']} not found"}), 404
            grant.pi_id = data['principalInvestigatorId']
        else: # pi_id is not nullable
             return jsonify({"error": "principalInvestigatorId (pi_id) cannot be null."}), 400


    if 'coPiIds' in data:
        grant.co_pis.clear()
        for co_pi_id in data['coPiIds']:
            co_pi = Researcher.query.get(co_pi_id)
            if not co_pi:
                return jsonify({"error": f"Co-PI Researcher with id {co_pi_id} not found"}), 404
            grant.co_pis.append(co_pi)

    if 'projectIds' in data:
        grant.projects.clear()
        for project_id in data['projectIds']:
            project = Project.query.get(project_id)
            if not project:
                return jsonify({"error": f"Project with id {project_id} not found"}), 404
            grant.projects.append(project)

    db.session.commit()
    return jsonify(grant_to_json(grant))

@grant_bp.route('/<int:id>', methods=['DELETE'])
def delete_grant(id):
    grant = Grant.query.get(id)
    if not grant:
        return jsonify({"error": "Grant not found"}), 404

    grant.co_pis.clear()
    grant.projects.clear()

    db.session.delete(grant)
    db.session.commit()

    return jsonify({"message": "Grant deleted successfully"}), 200
