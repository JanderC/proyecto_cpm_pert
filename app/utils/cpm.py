import networkx as nx

def calculate_critical_path(tasks, edges):
    """
    Calcula el camino crítico usando el algoritmo CPM.

    Args:
        tasks (dict): Diccionario de tareas {id: Task}
        edges (list): Lista de tuplas (tarea_predecesora_id, tarea_sucesora_id)

    Returns:
        dict: Resultados del análisis CPM, incluyendo detalles de cada tarea y métricas globales.
    """
    # Crear el grafo dirigido
    G = nx.DiGraph()

    # Añadir nodos con duración
    for task_id, task in tasks.items():
        duration = task.duration if task.duration is not None else task.expected_time
        if duration is None:
            duration = 0
        G.add_node(task_id, duration=duration)

    # Añadir aristas
    for pred_id, succ_id in edges:
        G.add_edge(pred_id, succ_id)

    # Validar que sea un DAG
    if not nx.is_directed_acyclic_graph(G):
        raise ValueError("El grafo contiene ciclos, no se puede calcular el CPM")

    # Orden topológico
    topological_order = list(nx.topological_sort(G))

    # Paso hacia adelante (Early Start & Finish)
    early_start = {}
    for node in topological_order:
        early_start[node] = max(
            [early_start[p] + G.nodes[p]['duration'] for p in G.predecessors(node)],
            default=0
        )
    early_finish = {node: early_start[node] + G.nodes[node]['duration'] for node in G.nodes()}

    # Duración total del proyecto
    project_duration = max(early_finish.values())

    # Paso hacia atrás (Late Start & Finish)
    late_finish = {}
    late_start = {}
    for node in reversed(topological_order):
        late_finish[node] = min(
            [late_start[s] for s in G.successors(node)],
            default=project_duration
        )
        late_start[node] = late_finish[node] - G.nodes[node]['duration']

    # Calcular holgura (Slack)
    slack = {node: late_start[node] - early_start[node] for node in G.nodes()}

    # Camino crítico
    critical_path = [node for node in G.nodes() if slack[node] == 0]

    # Resultados por tarea
    task_data = {}
    for task_id in tasks:
        task_data[task_id] = {
            'early_start': early_start[task_id],
            'early_finish': early_finish[task_id],
            'late_start': late_start[task_id],
            'late_finish': late_finish[task_id],
            'slack': slack[task_id],
            'is_critical': task_id in critical_path
        }

    return {
        'tasks': task_data,
        'critical_path': critical_path,
        'project_duration': project_duration
    }

