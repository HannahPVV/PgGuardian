from app.detectors.base import Detector


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
            pid = conn.get("pid")
            user = conn.get("usename")
            query = conn.get("query") or ""

            # Umbral sugerido: más de 5 minutos inactivo dentro de una transacción
            if state == "idle in transaction" and seconds_idle > 300:
                issues.append(
                    self._add_issue(
                        code="HLT001",
                        level="high",
                        title="Transacción inactiva abierta por demasiado tiempo",
                        desc=(
                            f"La sesión PID {pid}, del usuario '{user}', lleva "
                            f"{int(seconds_idle)} segundos en estado idle in transaction. "
                            "Esto puede retener locks, bloquear mantenimiento y afectar el rendimiento."
                        ),
                        table="",
                        sql_check=(
                            "SELECT pid, usename, state, "
                            "now() - state_change AS idle_time, query "
                            "FROM pg_stat_activity "
                            "WHERE state = 'idle in transaction';"
                        ),
                        sql_fix=(
                            f"-- Revisar la sesión antes de terminarla\n"
                            f"SELECT pg_terminate_backend({pid});"
                        )
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

