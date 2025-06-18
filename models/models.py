import enum
from app import db # Assuming db is initialized in app.py
from sqlalchemy.sql import func

class ComputeResourceType(enum.Enum):
    CPU = "CPU"
    GPU = "GPU"
    TPU = "TPU"

# New Enum for ComputeResource Status
class ComputeResourceStatus(enum.Enum):
    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"

class GrantStatus(enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"

# Association Tables
project_labs_table = db.Table('project_labs',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('lab_id', db.Integer, db.ForeignKey('lab.id'), primary_key=True)
)

project_compute_resources_table = db.Table('project_compute_resources',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('compute_resource_id', db.Integer, db.ForeignKey('compute_resource.id'), primary_key=True)
)

project_grants_table = db.Table('project_grants',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('grant_id', db.Integer, db.ForeignKey('grant.id'), primary_key=True)
)

grant_co_pis_table = db.Table('grant_co_pis',
    db.Column('grant_id', db.Integer, db.ForeignKey('grant.id'), primary_key=True),
    db.Column('researcher_id', db.Integer, db.ForeignKey('researcher.id'), primary_key=True)
)

class Researcher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    bio = db.Column(db.Text, nullable=True)
    department = db.Column(db.String(120), nullable=False) # Added
    lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), nullable=True)
    notes = db.relationship('Note', backref='researcher', lazy=True)
    # projects_pi defined in Project model backref
    # grants_pi defined in Grant model backref
    # led_labs defined in Lab model backref

class Lab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    principal_investigator_id = db.Column(db.Integer, db.ForeignKey('researcher.id'), nullable=True) # Added
    principal_investigator = db.relationship('Researcher', backref=db.backref('led_labs', lazy='dynamic'), foreign_keys=[principal_investigator_id]) # Added dynamic lazy loading
    members = db.relationship('Researcher', backref='lab', lazy='dynamic', foreign_keys=[Researcher.lab_id]) # Added dynamic lazy loading
    # projects defined in Project model backref

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    pi_id = db.Column(db.Integer, db.ForeignKey('researcher.id'), nullable=False)
    principal_investigator = db.relationship('Researcher', backref=db.backref('projects_pi', lazy='dynamic'), foreign_keys=[pi_id])
    labs = db.relationship('Lab', secondary=project_labs_table, lazy='subquery',
                           backref=db.backref('projects', lazy='dynamic'))
    compute_resources = db.relationship('ComputeResource', secondary=project_compute_resources_table, lazy='subquery',
                                       backref=db.backref('projects', lazy='dynamic'))
    grants = db.relationship('Grant', secondary=project_grants_table, lazy='subquery',
                             backref=db.backref('projects', lazy='dynamic'))
    # notes defined in Note model backref

class ComputeResource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.Enum(ComputeResourceType), nullable=False) # Maps to 'type'
    description = db.Column(db.Text, nullable=True)
    # New fields based on types.ts
    specification = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum(ComputeResourceStatus), nullable=False)
    cluster_type = db.Column(db.String(100), nullable=True) # 'clusterType'
    nodes = db.Column(db.Integer, nullable=True)
    cpus_per_node = db.Column(db.Integer, nullable=True) # 'cpusPerNode'
    gpus_per_node = db.Column(db.Integer, nullable=True) # 'gpusPerNode'
    memory_per_node = db.Column(db.String(50), nullable=True) # 'memoryPerNode'
    storage_per_node = db.Column(db.String(50), nullable=True) # 'storagePerNode'
    network_bandwidth = db.Column(db.String(50), nullable=True) # 'networkBandwidth'
    # projects relationship defined in Project model backref ('compute_resources')

class Grant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.Enum(GrantStatus), nullable=False, default=GrantStatus.PENDING)
    # New fields
    agency = db.Column(db.String(150), nullable=False)
    grant_number = db.Column(db.String(100), nullable=True, unique=True)
    proposal_due_date = db.Column(db.DateTime, nullable=True) # proposalDueDate
    award_date = db.Column(db.DateTime, nullable=True) # awardDate
    # Existing date fields
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    # PI and Co-PIs
    pi_id = db.Column(db.Integer, db.ForeignKey('researcher.id'), nullable=False) # principalInvestigatorId
    principal_investigator = db.relationship('Researcher', backref=db.backref('grants_pi', lazy='dynamic'), foreign_keys=[pi_id])
    co_pis = db.relationship('Researcher', secondary=grant_co_pis_table, lazy='dynamic', # Changed to dynamic
                             backref=db.backref('grants_co_pi', lazy='dynamic'))
    # projects relationship defined in Project model backref ('grants')

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    researcher_id = db.Column(db.Integer, db.ForeignKey('researcher.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    project = db.relationship('Project', backref=db.backref('notes', lazy='dynamic'))

    def __repr__(self):
        return f'<Note {self.id}>'
