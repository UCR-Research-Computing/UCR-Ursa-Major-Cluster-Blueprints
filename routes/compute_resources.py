from flask import Blueprint, request, jsonify
from models.models import ComputeResource, Project, ComputeResourceType, ComputeResourceStatus # Enums
from app import db

compute_resource_bp = Blueprint('compute_resource_bp', __name__)

# Re-using mini_project_to_json from other route files (ideally this would be in a shared module)
def mini_project_to_json(project):
    if not project:
        return None
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description
    }

def compute_resource_to_json(cr_obj):
    """Serializes a ComputeResource object to a dictionary."""
    projects_list = cr_obj.projects.all() if hasattr(cr_obj.projects, 'all') else cr_obj.projects

    return {
        "id": cr_obj.id,
        "name": cr_obj.name,
        "type": cr_obj.resource_type.value, # Enum value
        "description": cr_obj.description,
        "specification": cr_obj.specification,
        "status": cr_obj.status.value, # Enum value
        "cluster_type": cr_obj.cluster_type,
        "nodes": cr_obj.nodes,
        "cpus_per_node": cr_obj.cpus_per_node,
        "gpus_per_node": cr_obj.gpus_per_node,
        "memory_per_node": cr_obj.memory_per_node,
        "storage_per_node": cr_obj.storage_per_node,
        "network_bandwidth": cr_obj.network_bandwidth,
        "projects": [mini_project_to_json(p) for p in projects_list]
    }

@compute_resource_bp.route('', methods=['POST'])
def create_compute_resource():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    required_fields = ['name', 'type', 'specification', 'status']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    try:
        resource_type_enum = ComputeResourceType(data['type'])
    except ValueError:
        valid_types = [e.value for e in ComputeResourceType]
        return jsonify({"error": f"Invalid type '{data['type']}'. Must be one of {valid_types}"}), 400

    try:
        status_enum = ComputeResourceStatus(data['status'])
    except ValueError:
        valid_statuses = [e.value for e in ComputeResourceStatus]
        return jsonify({"error": f"Invalid status '{data['status']}'. Must be one of {valid_statuses}"}), 400

    new_cr = ComputeResource(
        name=data['name'],
        resource_type=resource_type_enum,
        specification=data['specification'],
        status=status_enum,
        description=data.get('description'),
        cluster_type=data.get('clusterType'), # JS naming to Python
        nodes=data.get('nodes'),
        cpus_per_node=data.get('cpusPerNode'),
        gpus_per_node=data.get('gpusPerNode'),
        memory_per_node=data.get('memoryPerNode'),
        storage_per_node=data.get('storagePerNode'),
        network_bandwidth=data.get('networkBandwidth')
    )

    if 'projectIds' in data and data['projectIds']:
        for project_id in data['projectIds']:
            project = Project.query.get(project_id)
            if not project:
                db.session.rollback() # Rollback if any project not found
                return jsonify({"error": f"Project with id {project_id} not found"}), 404
            new_cr.projects.append(project)

    db.session.add(new_cr)
    db.session.commit()
    return jsonify(compute_resource_to_json(new_cr)), 201

@compute_resource_bp.route('', methods=['GET'])
def get_compute_resources():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    resources_page = ComputeResource.query.paginate(page=page, per_page=per_page, error_out=False)
    resources_list = [compute_resource_to_json(cr) for cr in resources_page.items]

    return jsonify({
        "compute_resources": resources_list,
        "total_pages": resources_page.pages,
        "current_page": resources_page.page,
        "total_items": resources_page.total
    })

@compute_resource_bp.route('/<int:id>', methods=['GET'])
def get_compute_resource(id):
    cr = ComputeResource.query.get(id)
    if not cr:
        return jsonify({"error": "Compute Resource not found"}), 404
    return jsonify(compute_resource_to_json(cr))

@compute_resource_bp.route('/<int:id>', methods=['PUT'])
def update_compute_resource(id):
    cr = ComputeResource.query.get(id)
    if not cr:
        return jsonify({"error": "Compute Resource not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    cr.name = data.get('name', cr.name)
    cr.description = data.get('description', cr.description)
    cr.specification = data.get('specification', cr.specification)

    if 'type' in data:
        try:
            cr.resource_type = ComputeResourceType(data['type'])
        except ValueError:
            valid_types = [e.value for e in ComputeResourceType]
            return jsonify({"error": f"Invalid type '{data['type']}'. Must be one of {valid_types}"}), 400

    if 'status' in data:
        try:
            cr.status = ComputeResourceStatus(data['status'])
        except ValueError:
            valid_statuses = [e.value for e in ComputeResourceStatus]
            return jsonify({"error": f"Invalid status '{data['status']}'. Must be one of {valid_statuses}"}), 400

    cr.cluster_type = data.get('clusterType', cr.cluster_type)
    cr.nodes = data.get('nodes', cr.nodes)
    cr.cpus_per_node = data.get('cpusPerNode', cr.cpus_per_node)
    cr.gpus_per_node = data.get('gpusPerNode', cr.gpus_per_node)
    cr.memory_per_node = data.get('memoryPerNode', cr.memory_per_node)
    cr.storage_per_node = data.get('storagePerNode', cr.storage_per_node)
    cr.network_bandwidth = data.get('networkBandwidth', cr.network_bandwidth)

    if 'projectIds' in data:
        cr.projects.clear()
        for project_id in data['projectIds']:
            project = Project.query.get(project_id)
            if not project:
                # Not rolling back here, but erroring out.
                # Depending on desired atomicity, could collect all errors or rollback.
                return jsonify({"error": f"Project with id {project_id} not found"}), 404
            cr.projects.append(project)

    db.session.commit()
    return jsonify(compute_resource_to_json(cr))

@compute_resource_bp.route('/<int:id>', methods=['DELETE'])
def delete_compute_resource(id):
    cr = ComputeResource.query.get(id)
    if not cr:
        return jsonify({"error": "Compute Resource not found"}), 404

    # Many-to-many relationship with Project
    cr.projects.clear() # Remove associations from project_compute_resources table

    db.session.delete(cr)
    db.session.commit()

    return jsonify({"message": "Compute Resource deleted successfully"}), 200
