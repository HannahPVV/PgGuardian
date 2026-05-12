# En snapshot.py
from .pg_client import db_client 

# clase para guardar toda la información del snapshot en un solo objeto
class Snapshot:
    def __init__(self, table_stats, index_usage, index_defs, fks_health, config, 
                 live_activity, query_stats, lock_status):
        self.tables = table_stats
        self.indexes = index_usage
        self.index_definitions = index_defs
        self.fks_missing_idx = fks_health
        self.settings = config
        self.connections = live_activity
        self.slow_queries = query_stats
        self.locks = lock_status

def take_snapshot():
    print("Capturando tablas")
    table_stats = _get_table_health()
    
    print("Capturando índices")
    index_usage = _get_index_usage()
    
    print("Capturando definiciones")
    index_defs = _get_index_definitions()
    
    print("Capturando FKs")
    fks_health = _get_unindexed_fks()
    
    print("Capturando settings")
    config = _get_runtime_settings()
    
    print("Capturando sesiones")
    live_activity = _get_active_sessions()
    
    print("Capturando queries lentas")
    query_stats = _get_statement_stats()
    
    print("Capturando bloqueos")
    lock_status = _get_blocking_locks()

    return Snapshot(table_stats, index_usage, index_defs, fks_health, config, live_activity, 
                    query_stats, lock_status)


def _get_table_health():
#Captura estadísticas de bloat y vacuum 
    return db_client.execute_query("""
        SELECT schemaname, relname AS table_name, n_live_tup, n_dead_tup, 
            seq_scan, n_mod_since_analyze, last_autovacuum
        FROM pg_stat_user_tables
    """)

def _get_index_usage():
#Monitorear cual es la frecuencia de uso de los índices
    return db_client.execute_query("""
        SELECT schemaname, relname AS table_name, indexrelname AS index_name, 
            idx_scan, idx_tup_read, idx_tup_fetch
        FROM pg_stat_user_indexes
    """)

def _get_index_definitions():
# Consultar redundancia y duplicados en índices
    return db_client.execute_query("""
        SELECT schemaname, tablename, indexname, indexdef 
        FROM pg_indexes 
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
    """)

def _get_unindexed_fks():
# Detectar fks que no tienen índices asociados que pueden causar problemas de rendimiento en joins y deletes
    return db_client.execute_query("""
        SELECT 
            kcu.constraint_name AS fk_name, 
            kcu.table_name, 
            kcu.column_name
        FROM information_schema.key_column_usage kcu
        JOIN information_schema.table_constraints tc 
          ON kcu.constraint_name = tc.constraint_name 
         AND kcu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' 
          AND kcu.table_schema NOT IN ('pg_catalog', 'information_schema')
    """)

def _get_runtime_settings():
# Configuración de la memoria, workers, autovacuum que pueden afectar el rendimiento de la
    return db_client.execute_query("""
        SELECT name, setting, unit, context, short_desc
        FROM pg_settings 
        WHERE name IN ('shared_buffers', 'effective_cache_size', 'work_mem', 
                       'maintenance_work_mem', 'max_connections', 'autovacuum')
    """)

def _get_active_sessions():
# Conexión y actividad actual para detectar sesiones inactivas o bloqueos
    return db_client.execute_query("""
        SELECT pid, usename, state, 
            EXTRACT(EPOCH FROM (now() - state_change)) AS seconds_idle, 
            EXTRACT(EPOCH FROM (now() - query_start)) AS seconds_running,
            query
        FROM pg_stat_activity 
        WHERE state IS NOT NULL 
          AND backend_type = 'client backend'  
        ORDER BY state_change ASC;
    """)

def _get_statement_stats():
    #anlisis de las consultas más lentas para detectar posibles optimizaciones
    try:
        return db_client.execute_query("""
            SELECT query, calls, total_exec_time, mean_exec_time
            FROM pg_stat_statements 
            ORDER BY mean_exec_time DESC LIMIT 10
        """)
    except Exception:
        print("pg_stat_statements no está disponible")
        return []

def _get_blocking_locks():
# Consulta para detectar bloqueos activos y qué procesos los están causando
    return db_client.execute_query("""
        SELECT l.pid, l.relation::regclass AS locked_item, l.mode, l.granted,
            pg_blocking_pids(l.pid) AS blocked_by
        FROM pg_locks l
        WHERE l.relation IS NOT NULL 
          AND l.database = (SELECT oid FROM pg_database WHERE datname = current_database())
    """)