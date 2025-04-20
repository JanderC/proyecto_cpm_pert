from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models.models import Project, Task, TaskDependency
from app import db
from app.utils.cpm import calculate_critical_path
from app.utils.pert import calculate_pert
import json
from datetime import datetime, timedelta

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

@projects_bp.route('/')
@login_required
def index():
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('project/index.html', projects=projects)

@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        
        project = Project(
            name=name,
            description=description,
            user_id=current_user.id
        )   
        
        db.session.add(project)
        db.session.commit()
        
        flash('Proyecto creado con éxito!')
        return redirect(url_for('projects.view', project_id=project.id))  # Redirigir al 'view' después de crear el proyecto
    
    # ⬇️ En caso de GET, creamos un objeto vacío para que el template no falle
    empty_project = Project()
    return render_template('project/create.html', project=empty_project)

@projects_bp.route('/<int:project_id>')
@login_required
def view(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Verificar que el usuario actual sea el propietario
    if project.user_id != current_user.id:
        flash('No tienes permiso para ver este proyecto')
        return redirect(url_for('projects.index'))
    
    tasks = Task.query.filter_by(project_id=project_id).all()
    
    # Obtener relaciones de dependencia para visualización
    dependencies = []
    for task in tasks:
        for dep in task.dependencies:
            dependencies.append({
                'source': dep.dependency_id,
                'target': task.id,
                'type': dep.dependency_type
            })
    
    return render_template(
        'project/view.html', 
        project=project, 
        tasks=tasks,
        dependencies=json.dumps(dependencies)
    )

@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Verificar que el usuario actual sea el propietario del proyecto
    if project.user_id != current_user.id:
        flash('No tienes permiso para editar este proyecto')
        return redirect(url_for('projects.index'))
    
    # Cuando el formulario es enviado (POST)
    if request.method == 'POST':
        project.name = request.form['name']
        project.description = request.form.get('description', '')
        project.start_date = request.form.get('start_date', None)
        project.end_date = request.form.get('end_date', None)
        project.time_unit = request.form['time_unit']
        
        # Convertir las fechas si fueron proporcionadas
        if project.start_date:
            project.start_date = datetime.strptime(project.start_date, '%Y-%m-%d')
        if project.end_date:
            project.end_date = datetime.strptime(project.end_date, '%Y-%m-%d')
        
        db.session.commit()
        flash('Proyecto actualizado con éxito!')
        return redirect(url_for('projects.view', project_id=project.id))
    
    # Si el método es GET, simplemente renderizamos el formulario de edición
    return render_template('project/edit.html', project=project)

@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
def delete(project_id):
    project = Project.query.get_or_404(project_id)
    
    if project.user_id != current_user.id:
        flash('No tienes permiso para eliminar este proyecto')
        return redirect(url_for('projects.index'))
    
    db.session.delete(project)
    db.session.commit()
    
    flash('Proyecto eliminado con éxito')
    return redirect(url_for('projects.index'))

# --- TAREAS ---

@projects_bp.route('/<int:project_id>/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task(project_id):
    project = Project.query.get_or_404(project_id)
    
    if project.user_id != current_user.id:
        flash('No tienes permiso para añadir tareas a este proyecto')
        return redirect(url_for('projects.index'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        duration = request.form.get('duration')
        
        # Para PERT
        optimistic = request.form.get('optimistic')
        most_likely = request.form.get('most_likely')
        pessimistic = request.form.get('pessimistic')
        
        # Para CPM (campos nuevos)
        early_start = request.form.get('early_start')
        early_finish = request.form.get('early_finish')
        late_start = request.form.get('late_start')
        late_finish = request.form.get('late_finish')
        slack = request.form.get('slack')

        task = Task(
            name=name,
            description=description,
            project_id=project_id
        )
        
        # Valores para duración
        if duration:
            task.duration = float(duration)
        
        # Valores para PERT
        if all([optimistic, most_likely, pessimistic]):
            task.optimistic_time = float(optimistic)
            task.most_likely_time = float(most_likely)
            task.pessimistic_time = float(pessimistic)
            task.calculate_expected_time()
        
        # Nuevos campos para CPM
        if early_start:
            task.early_start = float(early_start)
        if early_finish:
            task.early_finish = float(early_finish)
        if late_start:
            task.late_start = float(late_start)
        if late_finish:
            task.late_finish = float(late_finish)
        if slack:
            task.slack = float(slack)
        
        db.session.add(task)
        db.session.commit()
        
        # Procesar dependencias si se especificaron
        dependency_ids = request.form.getlist('dependencies')
        for dep_id in dependency_ids:
            dependency = TaskDependency(
                task_id=task.id,
                dependency_id=int(dep_id),
                dependency_type='finish-to-start'
            )
            db.session.add(dependency)
        
        db.session.commit()
        
        flash('Tarea creada con éxito!')
        return redirect(url_for('projects.view', project_id=project_id))
    
    # Obtener todas las tareas existentes para seleccionar dependencias
    tasks = Task.query.filter_by(project_id=project_id).all()
    return render_template('task/create.html', project=project, tasks=tasks)

@projects_bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = Project.query.get(task.project_id)

    if project.user_id != current_user.id:
        flash('No tienes permiso para editar esta tarea')
        return redirect(url_for('projects.index'))

    # Obtener todas las tareas del proyecto excepto la actual (no puede depender de sí misma)
    tasks = Task.query.filter(Task.project_id == task.project_id, Task.id != task.id).all()

    if request.method == 'POST':
        # Actualizamos todos los campos relevantes
        task.name = request.form['name']
        task.description = request.form.get('description', '')

        # Actualizar duración
        if 'duration' in request.form and request.form['duration']:
            task.duration = int(request.form['duration'])

        # Nuevos campos de tiempo
        if 'early_start' in request.form and request.form['early_start']:
            task.early_start = float(request.form['early_start'])
        if 'early_finish' in request.form and request.form['early_finish']:
            task.early_finish = float(request.form['early_finish'])
        if 'late_start' in request.form and request.form['late_start']:
            task.late_start = float(request.form['late_start'])
        if 'late_finish' in request.form and request.form['late_finish']:
            task.late_finish = float(request.form['late_finish'])
        if 'slack' in request.form and request.form['slack']:
            task.slack = float(request.form['slack'])

        # Actualizar dependencias
        dependency_ids = request.form.getlist('dependencies')

        # Primero eliminar las actuales
        TaskDependency.query.filter_by(task_id=task.id).delete()

        # Luego agregar las nuevas
        for dep_id in dependency_ids:
            dependency = TaskDependency(
                task_id=task.id,
                dependency_id=int(dep_id),
                dependency_type='finish-to-start'
            )
            db.session.add(dependency)

        db.session.commit()
        flash('Tarea actualizada con éxito!')
        return redirect(url_for('projects.view', project_id=task.project_id))

    # Este bloque se ejecuta solo en GET o si hubo error
    current_dependencies = [dep.dependency_id for dep in task.dependencies]

    return render_template(
        'task/edit.html',
        task=task,
        project=project,
        tasks=tasks,
        current_dependencies=current_dependencies
    )


@projects_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = Project.query.get(task.project_id)
    
    if project.user_id != current_user.id:
        flash('No tienes permiso para eliminar esta tarea')
        return redirect(url_for('projects.index'))
    
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    
    flash('Tarea eliminada con éxito')
    return redirect(url_for('projects.view', project_id=project_id))

# --- ANÁLISIS DE PROYECTO ---

@projects_bp.route('/<int:project_id>/analyze')
@login_required
def analyze(project_id):
    project = Project.query.get_or_404(project_id)
    
    if project.user_id != current_user.id:
        flash('No tienes permiso para analizar este proyecto')
        return redirect(url_for('projects.index'))
    
    tasks = Task.query.filter_by(project_id=project_id).all()
    
    # Crear estructuras de datos
    task_dict = {task.id: task for task in tasks}
    edges = []

    for task in tasks:
        for dep in task.dependencies:
            edges.append((dep.dependency_id, task.id))
    
    # Calcular CPM y PERT
    cpm_result = calculate_critical_path(task_dict, edges)
    pert_result = calculate_pert(task_dict, edges)
    
    # Extraer resultados por tarea del CPM (solo claves que sean enteros)
    task_results = {k: v for k, v in cpm_result.items() if isinstance(k, int)}
    
    for task_id, values in task_results.items():
        task = task_dict[task_id]
        task.early_start = values['early_start']
        task.early_finish = values['early_finish']
        task.late_start = values['late_start']
        task.late_finish = values['late_finish']
        task.slack = values['slack']
        task.is_critical = values['is_critical']
    
    db.session.commit()
    
    return render_template(
        'project/analyze.html',
        project=project,
        tasks=tasks,
        critical_path=cpm_result['critical_path'],
        project_duration=cpm_result['project_duration'],
        pert_duration=pert_result['expected_duration'],
        pert_variance=pert_result['variance'],
        pert_std_dev=pert_result['std_dev']
    )

# Función para calcular la diferencia de días entre dos fechas
def days_between(start_date, end_date):
    if start_date and end_date:
        delta = end_date - start_date
        return delta.days
    return 0

@projects_bp.route('/<int:project_id>/gantt')
@login_required
def gantt(project_id):
    project = Project.query.get_or_404(project_id)

    if project.user_id != current_user.id:
        flash('No tienes permiso para ver este proyecto')
        return redirect(url_for('projects.index'))

    tasks = Task.query.filter_by(project_id=project_id).all()
    task_dict = {task.id: task for task in tasks}
    edges = []

    for task in tasks:
        for dep in task.dependencies:
            edges.append((dep.dependency_id, task.id))

    # Calcular CPM y actualizar campos en la BD
    cpm_result = calculate_critical_path(task_dict, edges)

    for task_id, values in cpm_result.items():
        if isinstance(task_id, int):  # Evitar 'critical_path' y 'project_duration'
            task = task_dict[task_id]
            task.early_start = values['early_start']
            task.early_finish = values['early_finish']
            task.late_start = values['late_start']
            task.late_finish = values['late_finish']
            task.slack = values['slack']
            task.is_critical = values['is_critical']

    db.session.commit()

    # 🔄 Recargar tareas desde la base de datos para obtener los datos actualizados
    tasks = Task.query.filter_by(project_id=project_id).all()

    # 📆 Fecha base del proyecto
    base_date = project.start_date or datetime.utcnow()

    # 📊 Preparar datos para el Gantt
    gantt_data = []
    for idx, task in enumerate(tasks):
        duration = task.duration or task.expected_time or 1

        # Usamos early_start como base si está disponible
        offset = task.early_start if task.early_start is not None else idx * 2
        task_start = base_date + timedelta(days=offset)
        task_end = task_start + timedelta(days=duration)

        gantt_data.append({
            'id': str(task.id),
            'name': task.name,
            'start': task_start.strftime('%Y-%m-%d'),
            'end': task_end.strftime('%Y-%m-%d'),
            'progress': 0,
            'dependencies': ",".join(str(dep.dependency_id) for dep in task.dependencies),
            'custom_class': 'bar-critical' if task.is_critical else '',
            'duration': duration,
            'is_critical': task.is_critical
        })

    return render_template(
        'project/gantt.html',
        project=project,
        gantt_data=gantt_data,
        days_between=days_between  # Asegúrate que esta función esté definida
    )
