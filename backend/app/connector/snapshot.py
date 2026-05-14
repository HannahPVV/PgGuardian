# En snapshot.py
from .pg_client import db_client 

# clase para guardar toda la información del snapshot en un solo objeto
class Snapshot:
    def __init__(self, table_stats, index_usage, index_defs, fks_health, config, 
                 live_activity, query_stats, lock_status, autovacuum_disabled, constraint_indexes, column_stats, refresh_statistics):
        self.tables = table_stats
        self.indexes = index_usage
        self.index_definitions = index_defs
        self.fks_missing_idx = fks_health
        self.settings = config
        self.connections = live_activity
        self.slow_queries = query_stats
        self.locks = lock_status
        self.autovacuum_disabled = autovacuum_disabled
        self.constraint_indexes = constraint_indexes
        self.column_stats = column_stats
        self.refresh_statistics = refresh_statistics


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

    print("Capturando autovacuum")                  
    autovacuum_disabled = _get_autovacuum_disabled() 

    print("Capturando constraints")
    constraint_indexes = _get_constraint_indexes()

    print("Capturando estadísticas de columnas")
    column_stats = _get_column_stats()

    print("Capturando llaves del sistema (PK/FK)")
    db_keys = _get_database_keys()

    print("Refrescando estadísticas para análisis dinámicos")
    refresh_statistics= _refresh_statistics()

    for stat in column_stats:
        # Si tabla, columna existe en nuestras llaves, marcamos True
        stat['is_key'] = (stat['tablename'], stat['column_name']) in db_keys

    return Snapshot(table_stats, index_usage, index_defs, fks_health, config, live_activity, 
                    query_stats, lock_status, autovacuum_disabled, constraint_indexes, column_stats,refresh_statistics)


def _get_table_health():
#Captura estadísticas de bloat y vacuum 
    return db_client.execute_query("""
        SELECT schemaname, relname AS table_name, n_live_tup, n_dead_tup, 
            seq_scan, n_mod_since_analyze, last_autovacuum,
             (SELECT relkind = 'p' FROM pg_class 
             WHERE relname = t.relname LIMIT 1) AS is_partitioned
        FROM pg_stat_user_tables t
    """)  

def _get_autovacuum_disabled():
    return db_client.execute_query("""
        SELECT relname AS table_name
        FROM pg_class
        WHERE relkind = 'r'
          AND COALESCE(reloptions::text, '') LIKE '%%autovacuum_enabled=false%%'
    """)     

def _get_index_usage():
    # Agregamos el NOT EXISTS para que no traiga PKs ni FKs
    return db_client.execute_query("""
        SELECT 
            i.schemaname, i.relname AS table_name, i.indexrelname AS index_name, 
            i.idx_scan, (t.seq_scan + t.idx_scan) AS table_activity 
        FROM pg_stat_user_indexes i
        JOIN pg_stat_user_tables t ON i.relid = t.relid
        JOIN pg_index ix ON i.indexrelid = ix.indexrelid
        WHERE i.schemaname = 'public'
          AND i.idx_scan = 0 
          -- FILTRO DINÁMICO CONTRA DUPLICADOS Y REGLAS
          AND NOT EXISTS (
              SELECT 1 
              FROM pg_index ix2
              WHERE ix2.indrelid = ix.indrelid    -- Misma tabla
                AND ix2.indexrelid != ix.indexrelid -- Que no sea el mismo índice
                AND ix2.indkey = ix.indkey        -- MISMAS COLUMNAS (Aquí se van el SKU y Category_id)
          )
          -- Filtro de integridad básico
          AND ix.indisunique = false
          AND ix.indisprimary = false
          -- Filtro de actividad para quitar tablas pequeñas (como categories)
          AND (t.seq_scan + t.idx_scan) > 1000
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

def _get_constraint_indexes():
    # Postgres sabe qué índices son constraints 
    return db_client.execute_query("""
        SELECT conname AS index_name
        FROM pg_constraint
        WHERE contype IN ('p', 'u')
    """)

def _get_runtime_settings():
# Configuración de la memoria, workers, autovacuum que pueden afectar el rendimiento de la
    return db_client.execute_query("""
        SELECT name, setting, unit, context, short_desc
        FROM pg_settings 
        WHERE name IN ('shared_buffers', 'effective_cache_size', 'work_mem', 
                       'maintenance_work_mem', 'max_connections', 'autovacuum',
                        'pg_stat_statements.max', 'log_min_duration_statement')
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
            SELECT query, calls, total_exec_time, mean_exec_time, temp_blks_written
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

def _refresh_statistics():
    #Analiza las tablas
    try:
        # LISTA DE TABLAS
        tables = db_client.execute_query("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        for t in tables:
            # Ejecutamos ANALYZE sobre cada tabla encontrada
            db_client.execute_query(f"ANALYZE {t['tablename']};")
    except Exception as e:
        print(f"Error: {e}")

def _get_database_keys():
    # Trae las PK y FK para marcar en nuestras estadísticas de columnas
    query = """
        SELECT relname as tabla, attname as columna
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
        WHERE con.contype IN ('p', 'f');
    """
    res = db_client.execute_query(query)
    # tuplas para comparar fácil
    return {(r['tabla'], r['columna']) for r in res}

def _get_column_stats():
    #Trae las estadísticas básicas para detectar col que tienen un valor muy dominante
    return db_client.execute_query("""
        SELECT s.tablename, s.attname as column_name, 
               (s.most_common_freqs[1] * 100) as max_freq,
               s.most_common_vals::text as vals, t.typname as d_type
        FROM pg_stats s
        JOIN pg_type t ON t.oid = (
            SELECT atttypid FROM pg_attribute 
            WHERE attrelid = s.tablename::regclass AND attname = s.attname
        )
        WHERE s.schemaname = 'public' AND s.most_common_freqs IS NOT NULL;
    """)



