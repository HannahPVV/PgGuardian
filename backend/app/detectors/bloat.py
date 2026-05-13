from detectors.base import Detector


class TableBloatDetector(Detector):
    
    # Detecta tablas con alto porcentaje de dead tuples (bloat).
 
    category = "bloat"

    def run(self, snap):
        issues = []

        for table in snap.tables:

            table_name = table.get("table_name")
            live_tuples = table.get("n_live_tup", 0)
            dead_tuples = table.get("n_dead_tup", 0)

            total_rows = live_tuples + dead_tuples

            # Evitar división entre cero
            if total_rows == 0:
                continue

            bloat_percent = (dead_tuples / total_rows) * 100

            # Clasificación de severidad
            if bloat_percent >= 40:
                severity = "high"
                title = "Bloat crítico detectado en tabla"

            elif bloat_percent >= 20:
                severity = "medium"
                title = "Bloat elevado detectado en tabla"

            else:
                continue

            issues.append(
                self._add_issue(
                    code="BLT001",
                    level=severity,
                    title=title,
                    desc=(
                        f"La tabla '{table_name}' tiene "
                        f"{dead_tuples} dead tuples de un total de "
                        f"{total_rows} registros "
                        f"({bloat_percent:.1f}% de bloat). "
                        "Esto puede afectar scans, VACUUM y rendimiento general."
                    ),
                    table=table_name,
                    sql_check=(
                        "SELECT relname, n_live_tup, n_dead_tup "
                        "FROM pg_stat_user_tables;"
                    ),
                    sql_fix=(
                        f"VACUUM ANALYZE {table_name};"
                    )
                )
            )

        return issues


class IndexBloatDetector(Detector):
    """
    Detector 8:
    Detecta posibles índices inflados o poco útiles.

    Se consideran sospechosos los índices nunca usados
    en tablas con alto número de dead tuples.
    """

    category = "bloat"

    def run(self, snap):
        issues = []

        # Crear mapa rápido de dead tuples por tabla
        dead_tuple_map = {}

        for table in snap.tables:
            table_name = table.get("table_name")
            dead_tuple_map[table_name] = table.get("n_dead_tup", 0)

        for idx in snap.indexes:

            index_name = idx.get("index_name")
            table_name = idx.get("table_name")
            idx_scan = idx.get("idx_scan", 0)

            dead_tuples = dead_tuple_map.get(table_name, 0)

            # Índice nunca usado + tabla con basura
            if idx_scan == 0 and dead_tuples >= 100:

                issues.append(
                    self._add_issue(
                        code="BLT002",
                        level="medium",
                        title="Posible índice inflado detectado",
                        desc=(
                            f"El índice '{index_name}' en la tabla "
                            f"'{table_name}' nunca ha sido utilizado "
                            f"y la tabla tiene {dead_tuples} dead tuples. "
                            "Esto puede indicar espacio desperdiciado o necesidad de mantenimiento."
                        ),
                        table=table_name,
                        sql_check=(
                            "SELECT relname, indexrelname, idx_scan "
                            "FROM pg_stat_user_indexes;"
                        ),
                        sql_fix=(
                            f"REINDEX INDEX {index_name};"
                        )
                    )
                )

        return issues

class AutovacuumDisabledDetector(Detector):
    #Detecta tablas con autovacuum desactivado explícitamente, lo cual puede causar bloat severo.
        
    category = "bloat"
    def run(self, snap):
        issues = []
        for table in snap.autovacuum_disabled:
            table_name = table.get("table_name")
            issues.append(
                self._add_issue(
                    code="BLT003",
                    level="high",
                    title=f"Autovacuum desactivado en '{table_name}'",
                    desc=(f"La tabla '{table_name}' tiene autovacuum desactivado "
                    "explícitamente. Esto impide la limpieza automática de "
                    "dead tuples y puede causar bloat severo con el tiempo."
                    ),table=table_name,
                    sql_check=(
                        "SELECT reloptions FROM pg_class "
                        f"WHERE relname = '{table_name}';"),
                    sql_fix=(
                     f"ALTER TABLE {table_name} RESET (autovacuum_enabled);")
                )
            )
            return issues