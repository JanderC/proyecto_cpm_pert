from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(256))
    projects = db.relationship('Project', backref='owner', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def calculate_cpm(self):
        # Lógica para calcular el camino crítico (CPM)
        pass
    
    def calculate_pert(self):
        # Lógica para calcular PERT
        pass

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)  # Duración en días o horas
    # Para PERT
    optimistic_time = db.Column(db.Float)
    most_likely_time = db.Column(db.Float)
    pessimistic_time = db.Column(db.Float)
    expected_time = db.Column(db.Float)  # Calculado: (o + 4m + p) / 6
    variance = db.Column(db.Float)  # Calculado: ((p - o) / 6) ^ 2
    # Para CPM
    early_start = db.Column(db.Float)
    early_finish = db.Column(db.Float)
    late_start = db.Column(db.Float)
    late_finish = db.Column(db.Float)
    slack = db.Column(db.Float)
    is_critical = db.Column(db.Boolean, default=False)
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    
    # Relaciones para gestionar dependencias entre tareas
    dependencies = db.relationship(
        'TaskDependency',   
        foreign_keys='TaskDependency.task_id',
        backref=db.backref('task', lazy='joined'),
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    dependents = db.relationship(
        'TaskDependency',
        foreign_keys='TaskDependency.dependency_id',
        backref=db.backref('dependency', lazy='joined'),
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<Task {self.name}>'
    
    def calculate_expected_time(self):
        if all([self.optimistic_time, self.most_likely_time, self.pessimistic_time]):
            self.expected_time = (self.optimistic_time + 4 * self.most_likely_time + self.pessimistic_time) / 6
            self.variance = ((self.pessimistic_time - self.optimistic_time) / 6) ** 2
            return self.expected_time
        return None

class TaskDependency(db.Model):
    __tablename__ = 'task_dependencies'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    dependency_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    dependency_type = db.Column(db.String(20), default='finish-to-start')  # finish-to-start, start-to-start, etc.
    
    __table_args__ = (db.UniqueConstraint('task_id', 'dependency_id', name='_task_dependency_uc'),)
    
    def __repr__(self):
        return f'<TaskDependency {self.task_id} -> {self.dependency_id}>'
    