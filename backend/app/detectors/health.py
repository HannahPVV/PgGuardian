from detectors.base import Detector


class IdleInTransactionDetector(Detector):
    """
    Detector 4:
    Detecta sesiones que están en estado 'idle in transaction'.
    Esto es peligroso porque una transacción abierta por mucho tiempo puede retener locks,
    impedir VACUUM y afectar el rendimiento de la base.
    """

    category = "health"

    def run(self, snap):
        issues = []

        for conn in snap.connections:
            state = conn.get("state")
            seconds_idle = conn.get("seconds_idle") or 0
            seconds_running = conn.get("seconds_running") or 0
            pid = conn.get("pid")
            user = conn.get("usename")
            query = conn.get("query") or ""

            tiempo_formateado = f"{int(seconds_idle // 60)} minutos" if seconds_idle >= 60 else f"{int(seconds_idle)} segundos"
          
            if state == "idle in transaction":
                if seconds_idle > 1800:
                    severity = "high"
                    title = "Transacción inactiva crítica — más de 30 minutos"
                elif seconds_idle > 300:
                    severity = "medium"
                    title = "Transacción inactiva — más de 5 minutos"
                else:
                    continue         
                issues.append(
                    self._add_issue(
                        code="HLT001",
                        level= severity,
                        title=title,
                        desc=(
                            f"El PID {pid} (usuario '{user}') lleva {tiempo_formateado} "
                            "inactivo dentro de una transacción abierta. Esto es peligroso "
                            "porque puede retener locks y bloquear el mantenimiento (VACUUM)."
                        ),
                        table="",
                        sql_check=(
                            "SELECT pid, usename, state, "
                            "now() - state_change AS idle_time, query "
                            "FROM pg_stat_activity "
                            "WHERE state = 'idle in transaction';"
                        ),
                        sql_fix=(
                            f"SELECT pg_terminate_backend({pid});"
                        )
                    )

                )
            elif state == "active" and "pg_sleep" in query.lower():
                # Aplicamos niveles según la duración de la query
                if seconds_running > 1800: # 30 min
                    severity = "high"
                    title = "Sesión crítica bloqueada por pg_sleep"
                elif seconds_running > 300: # 5 min
                    severity = "medium"
                    title = "Sesión prolongada detectada po pg_sleep"
                else:
                    continue # Menos de 5 min no se reporta

                issues.append(
                    self._add_issue(
                        code="HLT001",
                        level=severity,
                        title=title,
                        desc=(
                            f"El PID {pid} está ejecutando un bloqueo vía pg_sleep por {int(seconds_running // 60)} min. "
                        ),
                        table="",
                        sql_check=f"SELECT pid, query, now() - query_start FROM pg_stat_activity WHERE pid = {pid};",
                        sql_fix=f"SELECT pg_terminate_backend({pid});"
                    )
                )
        return issues



class ActiveLocksDetector(Detector):
    """
    Detector 5:
    Detecta locks activos no concedidos o procesos bloqueados por otros.
    Usa la información capturada desde pg_locks y pg_blocking_pids().
    """

    category = "health"

    def run(self, snap):
        issues = []

        for lock in snap.locks:
            pid = lock.get("pid")
            locked_item = lock.get("locked_item")
            mode = lock.get("mode")
            granted = lock.get("granted")
            blocked_by = lock.get("blocked_by")

            has_blocking_pid = blocked_by not in (None, [], "{}")

            # Reporta si el lock no fue concedido o si está bloqueado por otro proceso
            if granted is False or has_blocking_pid:
                issues.append(
                    self._add_issue(
                        code="HLT002",
                        level="high",
                        title="Bloqueo activo detectado",
                        desc=(
                            f"El proceso PID {pid} tiene un lock en '{locked_item}' "
                            f"con modo '{mode}'. Bloqueado por: {blocked_by}. "
                            "Esto puede causar esperas largas o congelar operaciones."
                        ),
                        table=str(locked_item) if locked_item else "",
                        sql_check=(
                            "SELECT l.pid, l.relation::regclass AS locked_item, "
                            "l.mode, l.granted, pg_blocking_pids(l.pid) AS blocked_by "
                            "FROM pg_locks l "
                            "WHERE l.relation IS NOT NULL;"
                        ),
                        sql_fix=(
                            "-- Identificar la query bloqueadora antes de matar procesos\n"
                            "SELECT pid, usename, state, query "
                            "FROM pg_stat_activity "
                            f"WHERE pid = ANY(ARRAY{blocked_by});"
                        )
                    )
                )

        return issues


class ConnectionSpikeDetector(Detector):
    """
    Detector 6:
    Detecta picos de conexiones comparando conexiones actuales contra max_connections.
    Usa snap.connections y snap.settings.
    """

    category = "health"

    def run(self, snap):
        issues = []

        total_connections = len(snap.connections)
        max_connections = None

        for setting in snap.settings:
            if setting.get("name") == "max_connections":
                try:
                    max_connections = int(setting.get("setting"))
                except (TypeError, ValueError):
                    max_connections = None
                break

        # Si no se encontró max_connections, no se puede evaluar bien.
        if max_connections is None or max_connections == 0:
            return issues

        usage_percent = (total_connections / max_connections) * 100

        if usage_percent >= 80:
            severity = "high"
        elif usage_percent >= 60:
            severity = "medium"
        else:
            return issues

        issues.append(
            self._add_issue(
                code="HLT003",
                level=severity,
                title="Uso elevado de conexiones",
                desc=(
                    f"La base de datos tiene {total_connections} conexiones activas "
                    f"de un máximo configurado de {max_connections} "
                    f"({usage_percent:.1f}% de uso). "
                    "Esto puede indicar un pico de conexiones o falta de pooling."
                ),
                table="",
                sql_check=(
                    "SELECT count(*) AS current_connections "
                    "FROM pg_stat_activity "
                    "WHERE datname = current_database(); "
                    "SHOW max_connections;"
                ),
                sql_fix=(
                    "-- Recomendación: revisar si la app usa connection pooling.\n"
                    "-- Opciones: PgBouncer, ajustar pool del backend o revisar max_connections."
                )
            )
        )

        return issues
    
class TableGrowDetector(Detector):
    #Detecta tablas que crecen sin control y no manejan particonamiento

    category = "health"

    def run(self, snap):
        issues = []
        
        # tiempo - 1 año en segundos (aprox 31,536,000 segundos)
        time = 31536000 

        for table in snap.tables:
            table_name = table.get("table_name")
            is_partitioned = table.get("is_partitioned") or False
            oldest_age = table.get("oldest_record_age_seconds") or 0
            
            # Solo se anlizan tablas que NO están particionadas
            if not is_partitioned:
                # Si tiene registros que superan el año de antigüedad
                if oldest_age > time:
                    
                    years_old = round(oldest_age / (365 * 24 * 3600), 1)
                    
                    issues.append(
                        self._add_issue(
                            code="HLT004",
                            level="medium", # Severidad MEDIA 
                            title=f"Crecimiento de tabla descontrolado: {table_name}",
                            desc=(
                                f"La tabla '{table_name}' no utiliza particionamiento y contiene "
                                f"registros de hace {years_old} años. Esto indica una acumulación "
                                "excesiva de datos históricos que puede degradar el rendimiento."
                            ),
                            table=table_name,
                            sql_check=(
                                f"SELECT MIN(created_at) AS oldest_record, count(*) AS total_rows "
                                f"FROM {table_name};"
                            ),
                            sql_fix=(
                                f"Implementar partcionamiento o filtrar datos antiguos:"
                                f"DELETE FROM {table_name} WHERE created_at < NOW() - INTERVAL '1 year';"
            
                            )
                        )
                    )

        return issues

