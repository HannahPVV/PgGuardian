from detectors.base import Detector

class ForeignKeyIndexDetector(Detector):
    
 #Detecta foreign keys que no tienen un índice asociado.
    
    category = "indexes"

    def run(self, snap):

        issues = []

        # Recorremos todas las foreign keys encontradas
        for fk in snap.fks_missing_idx:

            table_name = fk["table_name"]
            column_name = fk["column_name"]
            fk_name = fk["fk_name"]

            has_index = False

            # Buscar si existe un índice relacionado con esa columna
            for idx in snap.index_definitions:

                if idx["tablename"] == table_name:

                    # Revisamos si la columna aparece dentro de la definición del índice
                    if column_name in idx["indexdef"]:
                        has_index = True
                        break

            # Si no encontramos índice, reportamos problema
            if not has_index:

                issues.append(
                    self._add_issue(
                        code="IDX001",
                        level="high",
                        title="Foreign key sin índice",
                        desc=f"La FK '{fk_name}' en la tabla '{table_name}' "
                             f"usa la columna '{column_name}' pero no tiene índice asociado.",
                        table=table_name,
                        sql_check=f"""
                            Revisar FK:
                            {table_name}.{column_name}
                        """,
                        sql_fix=f"""
                            CREATE INDEX idx_{table_name}_{column_name}
                            ON {table_name}({column_name});
                        """
                    )
                )

        return issues


class UnusedIndexesDetector(Detector):
    
    #Detecta índices que nunca se usan.
    
    category = "indexes"

    def run(self, snap):

        issues = []

        constraint_names = {r["index_name"] for r in snap.constraint_indexes}

        for idx in snap.indexes:

            index_name = idx["index_name"]
            table_name = idx["table_name"]
            scans = idx["idx_scan"]

            if index_name in constraint_names:
                continue

            # Índice nunca usado
            if scans == 0:

                issues.append(
                    self._add_issue(
                        code="IDX002",
                        level="medium",
                        title="Índice nunca usado",
                        desc=f"El índice '{index_name}' de la tabla "
                             f"'{table_name}' no ha sido utilizado.",
                        table=table_name,
                        sql_check=f"""
                            SELECT *
                            FROM pg_stat_user_indexes
                            WHERE indexrelname = '{index_name}';
                        """,
                        sql_fix=f"""
                            DROP INDEX {index_name};
                        """
                    )
                )

        return issues


class DuplicateIndexesDetector(Detector):

    #Detecta índices duplicados o redundantes.

    category = "indexes"

    def run(self, snap):

        issues = []

        seen_indexes = {}

        for idx in snap.index_definitions:

            table_name = idx["tablename"]
            index_name = idx["indexname"]
            index_def = idx["indexdef"]

            # Normalizamos la definición para comparar
            try:
                normalized_def = index_def.split(" ON ")[1]
            except Exception:
                normalized_def = index_def

            key = (table_name, normalized_def)

            # Si ya vimos una definición igual, es duplicado
            if key in seen_indexes:

                original_index = seen_indexes[key]

                issues.append(
                    self._add_issue(
                        code="IDX003",
                        level="medium",
                        title="Índice duplicado",
                        desc=f"El índice '{index_name}' parece duplicado "
                             f"del índice '{original_index}' en la tabla '{table_name}'.",
                        table=table_name,
                        sql_check=f"""
                            Revisar índices:
                            {original_index}
                            {index_name}
                        """,
                        sql_fix=f"""
                            DROP INDEX {index_name};
                        """
                    )
                )

            else:
                seen_indexes[key] = index_name

        return issues
    
class PartialIndexDetector(Detector):
    category = "indexes"

    def run(self, snap):
        issues = []
        tipos_ok = ['bool', 'varchar', 'text', 'int2', 'int4']

        for st in snap.column_stats:
            # Si tiene sesgo, es el tipo de dato correcto y NO es PK/FK
            if (st.get("max_freq", 0) > 90 and 
                st.get("d_type") in tipos_ok and 
                not st.get("is_key")):
                
                tab, col = st["tablename"], st["column_name"]
                val = st["vals"].replace("{", "").replace("}", "").split(",")[0]

                issues.append(self._add_issue(
                    code="IDX004",
                    level="medium",
                    title=f"Índice parcial en {tab}.{col}",
                    desc=f"Valor '{val}' domina el {st['max_freq']:.1f}% de la tabla.",
                    table=tab,
                    sql_check=f"SELECT {col}, count(*) FROM {tab} GROUP BY 1 ORDER BY 2 DESC;",
                    sql_fix=f"CREATE INDEX idx_{tab}_{col}_part ON {tab}({col}) WHERE {col} != '{val}';"
                ))
        return issues