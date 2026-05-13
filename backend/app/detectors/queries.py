from app.detectors.base import Detector


class TopQueriesDetector(Detector):
    """
    Detector 10: Top queries por consumo de recursos.
    Usa snap.slow_queries, basado en pg_stat_statements.
    """

    category = "performance"

    def run(self, snap):
        issues = []

        # Si el snapshot no trae queries, no se reporta nada.
        if not hasattr(snap, "slow_queries") or not snap.slow_queries:
            return issues

        # Tomamos las 5 queries con mayor tiempo total.
        top_queries = sorted(
            snap.slow_queries,
            key=lambda x: x.get("total_exec_time", 0),
            reverse=True
        )[:5]

        for query_data in top_queries:
            query_text = query_data.get("query", "")
            query_lower = query_text.lower()
            total_time = query_data.get("total_exec_time", 0)
            calls = query_data.get("calls", 0)
            db_name = query_data.get("datname", "N/A")
            temp_blks = query_data.get("temp_blks_written", 0)

            # Reporte general de query de alto impacto.
            if total_time > 500:
                issues.append(
                    self._add_issue(
                        code="PRF001",
                        level="medium",
                        title="Query de alto impacto detectada",
                        desc=(
                            f"La consulta en la base '{db_name}' acumuló "
                            f"{total_time:.2f} ms en {calls} llamadas. "
                            "Es una de las 5 queries que más recursos consume."
                        ),
                        table="",
                        sql_check=(
                            "SELECT query, calls, total_exec_time "
                            "FROM pg_stat_statements "
                            "ORDER BY total_exec_time DESC "
                            "LIMIT 5;"
                        ),
                        sql_fix=(
                            "-- Ejecutar EXPLAIN ANALYZE sobre la query.\n"
                            "-- Revisar si necesita índices o reescritura.\n"
                            f"-- Query: {query_text[:100]}..."
                        )
                    )
                )

            # LIKE con comodín inicial evita uso normal de índices B-Tree.
            if "like '%" in query_lower:
                issues.append(
                    self._add_issue(
                        code="PRF002",
                        level="medium",
                        title="Uso de comodín inicial en LIKE",
                        desc=(
                            "Se detectó un LIKE con '%' al inicio. "
                            "Esto puede impedir el uso eficiente de índices B-Tree."
                        ),
                        table="",
                        sql_check=(
                            "SELECT query "
                            "FROM pg_stat_statements "
                            "WHERE query ILIKE '%LIKE ''''%%';"
                        ),
                        sql_fix=(
                            "-- Considerar búsqueda de texto completo con tsvector "
                            "o revisar el uso de pg_trgm."
                        )
                    )
                )

            # Si escribe bloques temporales, puede indicar sort/hash en disco.
            if temp_blks > 0:
                issues.append(
                    self._add_issue(
                        code="PRF003",
                        level="high",
                        title="Query usando bloques temporales en disco",
                        desc=(
                            f"Esta consulta escribió {temp_blks} bloques temporales. "
                            "Puede indicar falta de memoria para ordenamientos, joins o agrupaciones."
                        ),
                        table="",
                        sql_check=(
                            "SELECT query, temp_blks_written "
                            "FROM pg_stat_statements "
                            "WHERE temp_blks_written > 0 "
                            "ORDER BY temp_blks_written DESC;"
                        ),
                        sql_fix=(
                            "-- Revisar work_mem y optimizar ORDER BY, GROUP BY o JOIN."
                        )
                    )
                )

            # Caso específico de demo: consulta costosa sobre orders.
            if "from orders" in query_lower and total_time > 500:
                issues.append(
                    self._add_issue(
                        code="PRF004",
                        level="high",
                        title="Query costosa sobre tabla grande",
                        desc=(
                            "Se detectó una query frecuente o costosa sobre 'orders'. "
                            "Puede requerir índices o revisión del plan de ejecución."
                        ),
                        table="orders",
                        sql_check=(
                            "SELECT query, calls, total_exec_time "
                            "FROM pg_stat_statements "
                            "WHERE query ILIKE '%from orders%' "
                            "ORDER BY total_exec_time DESC;"
                        ),
                        sql_fix=(
                            "-- Ejecutar EXPLAIN ANALYZE.\n"
                            "-- Revisar si falta índice en columnas usadas en WHERE o JOIN."
                        )
                    )
                )

            # Pocas llamadas con mucho tiempo puede indicar query muy pesada.
            if calls < 10 and total_time > 2000:
                issues.append(
                    self._add_issue(
                        code="PRF005",
                        level="medium",
                        title="Query poco frecuente pero muy costosa",
                        desc=(
                            f"La consulta tiene solo {calls} llamadas, pero acumuló "
                            f"{total_time:.2f} ms. Puede ser una query pesada o mal optimizada."
                        ),
                        table="",
                        sql_check=(
                            "SELECT query, calls, total_exec_time "
                            "FROM pg_stat_statements "
                            "WHERE calls < 10 "
                            "ORDER BY total_exec_time DESC;"
                        ),
                        sql_fix=(
                            "-- Ejecutar ANALYZE y revisar el plan con EXPLAIN ANALYZE."
                        )
                    )
                )

        return issues