from app import ma, db # Import ma and db from app.py
# Import all necessary models
from models.models import Researcher, Note, Lab, Project, ComputeResource, Grant, \
    ComputeResourceType, ComputeResourceStatus # Enums
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow import fields
from marshmallow_enum import EnumField # Import EnumField

# --- Note Schemas ---
class NoteSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Note
        load_instance = True
        sqla_session = db.session
        include_fk = True
        fields = ("id", "content", "created_at", "updated_at", "researcher_id", "project_id")

# --- Mini Schemas for concise nested representations ---
class MiniResearcherSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Researcher
        sqla_session = db.session
        fields = ("id", "name", "email", "department")

class MiniLabSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Lab
        sqla_session = db.session
        fields = ("id", "name")

class MiniProjectSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Project
        sqla_session = db.session
        fields = ("id", "name", "description")

class MiniComputeResourceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ComputeResource
        sqla_session = db.session
        # Include resource_type because it's key for identification
        fields = ("id", "name", "resource_type")

class MiniGrantSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Grant
        sqla_session = db.session
        fields = ("id", "title", "agency", "status")


# --- Researcher Schemas ---
class ResearcherSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Researcher
        load_instance = True
        sqla_session = db.session
        include_relationships = True # Handles 'notes', 'led_labs', etc. for dumping

    name = auto_field(required=True)
    email = fields.Email(required=True)
    department = auto_field(required=True)
    bio = auto_field(required=False, allow_none=True)
    lab_id = fields.Integer(required=False, allow_none=True) # For associating with a Lab

    # Output fields for relationships
    notes = fields.List(fields.Nested(NoteSchema), dump_only=True)
    # Use string "LabSchema" for forward declaration if LabSchema is defined later or to break circularity.
    # However, MiniLabSchema is better here if only id/name needed.
    led_labs = fields.List(fields.Nested(MiniLabSchema), dump_only=True) # Labs this researcher is PI for
    # lab (membership) is implicitly handled by lab_id for load, and for dump, could be:
    # lab = fields.Nested(MiniLabSchema, dump_only=True) # if model has 'lab' relationship for Researcher.lab_id

class ResearcherUpdateSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Researcher
        load_instance = True
        sqla_session = db.session
        # partial=True will be used at instantiation in route

    name = auto_field(required=False)
    email = fields.Email(required=False, allow_none=True)
    department = auto_field(required=False)
    bio = auto_field(required=False, allow_none=True)
    lab_id = fields.Integer(required=False, allow_none=True)

    notes = fields.List(fields.Nested(NoteSchema), dump_only=True)
    led_labs = fields.List(fields.Nested(MiniLabSchema), dump_only=True)


# --- Lab Schema ---
class LabSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Lab
        load_instance = True
        sqla_session = db.session
        include_relationships = False # Define explicitly

    name = auto_field(required=True)
    description = auto_field(required=False, allow_none=True) # Model has nullable=True

    # Input fields for IDs
    principal_investigator_id = fields.Integer(required=False, allow_none=True, load_only=True, data_key="principalInvestigatorId")
    project_ids = fields.List(fields.Integer(), required=False, load_only=True, data_key="projectIds")

    # Output fields for relationships
    principal_investigator = fields.Nested(MiniResearcherSchema, dump_only=True)
    members = fields.List(fields.Nested(MiniResearcherSchema), dump_only=True)
    projects = fields.List(fields.Nested(MiniProjectSchema), dump_only=True)


# --- Project Schema ---
class ProjectSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Project
        load_instance = True
        sqla_session = db.session
        include_relationships = False

    name = auto_field(required=True)
    description = auto_field(required=False, allow_none=True) # Model has nullable=True
    start_date = fields.DateTime(required=True)
    end_date = fields.DateTime(required=False, allow_none=True)

    pi_id = fields.Integer(required=True, data_key="leadResearcherId", load_only=True)
    lab_ids = fields.List(fields.Integer(), required=False, load_only=True, data_key="labIds")
    compute_resource_ids = fields.List(fields.Integer(), required=False, load_only=True, data_key="computeResourceIds")
    grant_ids = fields.List(fields.Integer(), required=False, load_only=True, data_key="grantIds")

    principal_investigator = fields.Nested(MiniResearcherSchema, dump_only=True, attribute="principal_investigator")
    labs = fields.List(fields.Nested(MiniLabSchema), dump_only=True)
    compute_resources = fields.List(fields.Nested(MiniComputeResourceSchema), dump_only=True)
    grants = fields.List(fields.Nested(MiniGrantSchema), dump_only=True)
    notes = fields.List(fields.Nested(NoteSchema), dump_only=True)


# --- ComputeResource Schema ---
class ComputeResourceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ComputeResource
        load_instance = True
        sqla_session = db.session
        include_relationships = False

    name = auto_field(required=True)
    # The model stores 'resource_type', JSON API uses 'type'
    resource_type = EnumField(ComputeResourceType, by_value=True, required=True, data_key="type")
    specification = auto_field(required=True) # Model: nullable=False
    status = EnumField(ComputeResourceStatus, by_value=True, required=True) # Model: nullable=False

    description = auto_field(required=False, allow_none=True) # Model: nullable=True
    cluster_type = auto_field(required=False, allow_none=True, data_key="clusterType") # Model: nullable=True
    nodes = fields.Integer(required=False, allow_none=True) # Model: nullable=True
    cpus_per_node = fields.Integer(required=False, allow_none=True, data_key="cpusPerNode") # Model: nullable=True
    gpus_per_node = fields.Integer(required=False, allow_none=True, data_key="gpusPerNode") # Model: nullable=True
    memory_per_node = auto_field(required=False, allow_none=True, data_key="memoryPerNode") # Model: nullable=True
    storage_per_node = auto_field(required=False, allow_none=True, data_key="storagePerNode") # Model: nullable=True
    network_bandwidth = auto_field(required=False, allow_none=True, data_key="networkBandwidth") # Model: nullable=True

    project_ids = fields.List(fields.Int(), data_key="projectIds", required=False, load_only=True)
    projects = fields.List(fields.Nested(MiniProjectSchema), dump_only=True)


# --- Grant Schema ---
class GrantSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Grant
        load_instance = True
        sqla_session = db.session
        include_relationships = False # Define explicitly

    # Core fields - required status inferred from model's nullable=False
    # Model fields: title(F), description(T), amount(F), status(F), agency(F)
    # grant_number(T), proposal_due_date(T), award_date(T), start_date(T), end_date(T)
    # pi_id(F)

    title = auto_field(required=True)
    agency = auto_field(required=True)
    amount = auto_field(required=True)
    status = EnumField(GrantStatus, by_value=True, required=True) # model default, but treat as req for input

    description = auto_field(required=False, allow_none=True)
    grant_number = auto_field(required=False, allow_none=True, data_key="grantNumber")

    # Date fields
    # Assuming start_date and end_date from prompt are required for a new grant, overriding model's nullable=True
    start_date = fields.DateTime(required=True, data_key="startDate")
    end_date = fields.DateTime(required=True, data_key="endDate")
    proposal_due_date = fields.DateTime(required=False, allow_none=True, data_key="proposalDueDate")
    award_date = fields.DateTime(required=False, allow_none=True, data_key="awardDate")

    # Input for relationships (load_only)
    # `pi_id` is the actual model field name. `data_key` maps JSON key.
    pi_id = fields.Integer(required=True, data_key="principalInvestigatorId", load_only=True)
    co_pi_ids = fields.List(fields.Integer(), required=False, load_only=True, data_key="coPiIds")
    project_ids = fields.List(fields.Integer(), required=False, load_only=True, data_key="projectIds")

    # Output for relationships (dump_only)
    principal_investigator = fields.Nested(MiniResearcherSchema, dump_only=True) # Attr name matches model
    co_pis = fields.List(fields.Nested(MiniResearcherSchema), dump_only=True)
    projects = fields.List(fields.Nested(MiniProjectSchema), dump_only=True)

# --- Grant Schema ---
# (To be added in Part 5 - Grant Schemas and Routes)
# For now, MiniGrantSchema is used by ProjectSchema.
# If a full GrantSchema is needed by another schema before it's fully defined,
# use fields.Nested("GrantSchema", only=(...), dump_only=True)
# For now, MiniGrantSchema is sufficient for Project output.
