import networkx as nx
import math
from .cpm import calculate_critical_path

def calculate_pert(tasks, edges):
    """
    Calcula el análisis PERT para un proyecto.
    
    Args:
        tasks (dict): Diccionario de tareas {id: Task}
        edges (list): Lista de tuplas (tarea_predecesora_id, tarea_sucesora_id)
    
    Returns:
        dict: Resultados del análisis PERT
    """
    # Crear un grafo dirigido
    G = nx.DiGraph()
    
    # Calcular tiempo esperado y varianza para cada tarea si no se ha hecho
    for task_id, task in tasks.items():
        if task.expected_time is None and all([task.optimistic_time, task.most_likely_time, task.pessimistic_time]):
            task.calculate_expected_time()
        
        # Usar tiempo esperado o duración como fallback
        duration = task.expected_time if task.expected_time is not None else task.duration
        if duration is None:
            duration = 0
            
        variance = task.variance if task.variance is not None else 0
        
        G.add_node(task_id, duration=duration, variance=variance)
    
    # Agregar aristas
    for edge in edges:
        G.add_edge(edge[0], edge[1])
    
    # Verificar si hay ciclos
    if not nx.is_directed_acyclic_graph(G):
        raise ValueError("El grafo contiene ciclos, no se puede calcular PERT")
    
    # Calcular CPM usando los tiempos esperados
    cpm_result = calculate_critical_path(tasks, edges)
    critical_path = cpm_result['critical_path']
    project_duration = cpm_result['project_duration']
    
    # Calcular la varianza total del proyecto (suma de varianzas en el camino crítico)
    total_variance = sum(G.nodes[task_id]['variance'] for task_id in critical_path)
    
    # Calcular la desviación estándar
    std_dev = math.sqrt(total_variance)
    
    # Calcular probabilidades para diferentes escenarios
    probabilities = {}
    
    # Probabilidad de completar en el tiempo esperado
    probabilities['expected'] = 0.5  # Por definición

    # Calcular probabilidades para diferentes plazos
    from scipy.stats import norm
    
    def get_completion_probability(target_time):
        """Calcula la probabilidad de completar el proyecto en un tiempo determinado"""
        if std_dev == 0:
            # Si la desviación estándar es cero, la probabilidad es 0 o 1
            return 1.0 if target_time >= project_duration else 0.0
        
        # Calcular el valor Z
        z_value = (target_time - project_duration) / std_dev
        
        # Obtener probabilidad de la distribución normal
        probability = norm.cdf(z_value)
        return probability
    
    # Calcular probabilidades para algunos escenarios comunes
    probabilities['early'] = get_completion_probability(project_duration - std_dev)
    probabilities['late'] = get_completion_probability(project_duration + std_dev)
    probabilities['very_early'] = get_completion_probability(project_duration - 2 * std_dev)
    probabilities['very_late'] = get_completion_probability(project_duration + 2 * std_dev)
    
    # Preparar los resultados
    results = {
        'expected_duration': project_duration,
        'variance': total_variance,
        'std_dev': std_dev,
        'critical_path': critical_path,
        'probabilities': probabilities
    }
    
    return results