import re

from detectors.base import Detector


class TopQueriesDetector(Detector):
    """
    Categoría 3: Queries problemáticas.
    Revisa queries provenientes de pg_stat_statements y, si existe,
    información de EXPLAIN / EXPLAIN ANALYZE.
    """

    category = "performance"

    def run(self, snap):
        issues = []

        if not hasattr(snap, "slow_queries") or not snap.slow_queries:
            return issues

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
            temp_blks = query_data.get("temp_blks_written", 0)

            explain_text = self._get_explain_text(query_data)
            estimated_rows = query_data.get("estimated_rows")
            actual_rows = query_data.get("actual_rows")

            if self._detect_h09_seq_scan_orders(query_lower, explain_text):
                issues.append(
                    self._add_issue(
                        code="H09",
                        level="high",
                        title="Query con Seq Scan en orders",
                        desc=(
                            "Se detectó una query sobre orders que presenta Seq Scan. "
                            "Esto puede indicar que la consulta se beneficiaría de un índice, "
                            "especialmente si filtra por customer_id."
                        ),
                        table="orders",
                        sql_check=(
                            "EXPLAIN (ANALYZE, BUFFERS) "
                            "SELECT count(*) FROM orders WHERE customer_id = $1;"
                        ),
                        sql_fix=(
                            "-- Recomendación: crear o revisar el índice relacionado con customer_id.\n"
                            "CREATE INDEX IF NOT EXISTS idx_orders_customer_id "
                            "ON orders(customer_id);"
                        )
                    )
                )

            if self._detect_h10_mismatch_rows(
                query_lower,
                estimated_rows,
                actual_rows
            ):
                issues.append(
                    self._add_issue(
                        code="H10",
                        level="high",
                        title="Mismatch entre filas estimadas y filas reales",
                        desc=(
                            f"El planner estimó {estimated_rows} filas, pero la ejecución real "
                            f"tuvo {actual_rows}. Una diferencia mayor a 5x puede indicar "
                            "estadísticas obsoletas."
                        ),
                        table="products",
                        sql_check=(
                            "EXPLAIN ANALYZE "
                            "SELECT * FROM products;"
                        ),
                        sql_fix=(
                            "ANALYZE products;\n"
                            "-- También revisar la frecuencia de auto-analyze."
                        )
                    )
                )

            if self._detect_h11_sort_disk(temp_blks, explain_text):
                issues.append(
                    self._add_issue(
                        code="H11",
                        level="high",
                        title="Query con sort en disco",
                        desc=(
                            f"La query escribió {temp_blks} bloques temporales o el plan "
                            "muestra un sort en disco. Esto puede indicar work_mem insuficiente "
                            "para la consulta."
                        ),
                        table="",
                        sql_check=(
                            "EXPLAIN (ANALYZE, BUFFERS) "
                            "-- Query afectada por sort en disco"
                        ),
                        sql_fix=(
                            "-- Recomendación: aumentar work_mem para queries de reporte "
                            "o reescribir ORDER BY / GROUP BY.\n"
                            "SET work_mem = '64MB';"
                        )
                    )
                )

            if self._detect_h12_like_pattern(query_text):
                issues.append(
                    self._add_issue(
                        code="H12",
                        level="medium",
                        title="Query con LIKE usando comodín inicial",
                        desc=(
                            "Se detectó un patrón LIKE con '%' al inicio. "
                            "Este anti-pattern puede impedir el uso eficiente de índices B-Tree."
                        ),
                        table="products",
                        sql_check=(
                            "SELECT query "
                            "FROM pg_stat_statements "
                            "WHERE query ILIKE '%LIKE%';"
                        ),
                        sql_fix=(
                            "-- Opciones recomendadas:\n"
                            "-- 1. Usar full-text search con tsvector + GIN.\n"
                            "-- 2. Usar pg_trgm con índice GIN.\n"
                            "-- 3. Cambiar la lógica de búsqueda si es posible."
                        )
                    )
                )

            if self._detect_h05_covering_index(query_lower):
                issues.append(
                    self._add_issue(
                        code="H05",
                        level="low",
                        title="Falta índice cubriente para reporte frecuente",
                        desc=(
                            "Se detectó una query de reporte sobre orders que filtra por "
                            "customer_id y consulta columnas como id, total u order_date. "
                            "Podría beneficiarse de un índice covering con INCLUDE."
                        ),
                        table="orders",
                        sql_check=(
                            "SELECT id, total, order_date "
                            "FROM orders "
                            "WHERE customer_id = $1;"
                        ),
                        sql_fix=(
                            "CREATE INDEX IF NOT EXISTS idx_orders_customer_covering "
                            "ON orders(customer_id) INCLUDE (total, order_date);"
                        )
                    )
                )

        return issues

    def _get_explain_text(self, query_data):
        plan = query_data.get("plan", "")
        explain = query_data.get("explain", "")
        explain_text = query_data.get("explain_text", "")

        return f"{plan} {explain} {explain_text}".lower()

    def _detect_h09_seq_scan_orders(self, query_lower, explain_text):
        has_orders = "from orders" in query_lower or "on orders" in explain_text
        has_seq_scan = "seq scan" in explain_text and "orders" in explain_text

        return has_orders and has_seq_scan

    def _detect_h10_mismatch_rows(self, query_lower, estimated_rows, actual_rows):
        if "products" not in query_lower:
            return False

        if estimated_rows is None or actual_rows is None:
            return False

        try:
            estimated = float(estimated_rows)
            actual = float(actual_rows)
        except (TypeError, ValueError):
            return False

        if estimated <= 0:
            return False

        ratio = max(estimated, actual) / min(estimated, actual)

        return ratio > 5

    def _detect_h11_sort_disk(self, temp_blks, explain_text):
        has_temp_blocks = temp_blks is not None and temp_blks > 0
        has_external_sort = (
            "sort method: external merge" in explain_text
            or "disk:" in explain_text
            or "temp read" in explain_text
            or "temp written" in explain_text
        )

        return has_temp_blocks or has_external_sort

    def _detect_h12_like_pattern(self, query_text):
        pattern = r"like\s+['\"]%[^'\"]*['\"]"
        return re.search(pattern, query_text, re.IGNORECASE) is not None

    def _detect_h05_covering_index(self, query_lower):
        has_orders = "from orders" in query_lower
        filters_customer = "customer_id" in query_lower
        selects_report_columns = (
            "order_date" in query_lower
            or "total" in query_lower
            or "select id" in query_lower
        )

        return has_orders and filters_customer and selects_report_columns