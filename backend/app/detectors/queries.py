from detectors.base import Detector

class TopQueriesDetector(Detector):
    # Analiza pg_stat_statements para identificar las 5 queries que consumen más tiempo total en la base de datos.

    category = "performance"

    def run(self, snap):
        issues = []
        
        # Ordenamos las queries del snapshot por tiempo total (descendente) y tomamos las primeras 5.
        top_queries = sorted(
            snap.slow_queries, 
            key=lambda x: x.get("total_exec_time", 0), 
            reverse=True
        )[:5]

        for query_data in top_queries:
            total_time = query_data.get("total_exec_time", 0)
            calls = query_data.get("calls", 0)
            query_text = query_data.get("query", "Query desconocida")
            db_name = query_data.get("datname", "N/A")

            # Solo reportamos si el tiempo total es significativo 
            if total_time > 100:
                issues.append(
                    self._add_issue(
                        code="PRF001",
                        level="medium",
                        title="Query de alto impacto detectada",
                        desc=(
                            f"La consulta en la base '{db_name}' ha acumulado {total_time:.2f} ms "
                            f"de ejecución en {calls} llamadas. Es una de las top 5 que más recursos consume."
                        ),
                        table="",
                        sql_check="SELECT query, calls, total_exec_time FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 5;",
                        sql_fix=(
                            "-- Recomendación: Ejecutar EXPLAIN ANALYZE sobre la query para identificar "
                            "-- si requiere índices nuevos o una reescritura.\n"
                            f"-- Query: {query_text[:100]}..."
                        )
                    )
                )
        
        return issues


