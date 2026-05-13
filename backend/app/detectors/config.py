from app.detectors.base import Detector


class ConfigurationDetector(Detector):
    """
    Detector 9: Configuración y Carga.
    Revisa parámetros desde snap.settings.
    """

    category = "configuration"

    def run(self, snap):
        issues = []

        # Convertimos settings a diccionario para buscarlos por nombre.
        settings = self._settings_to_dict(snap.settings)

        issues.extend(self._check_shared_buffers(settings))
        issues.extend(self._check_work_mem(settings))
        issues.extend(self._check_pg_stat_statements_max(settings))
        issues.extend(self._check_log_min_duration_statement(settings))

        return issues

    def _settings_to_dict(self, raw_settings):
        # Convierte la lista de settings en diccionario.
        settings = {}

        for setting in raw_settings:
            name = setting.get("name")
            if name:
                settings[name] = setting

        return settings

    def _get_setting(self, settings, name):
        # Regresa el parámetro solicitado o un diccionario vacío.
        return settings.get(name, {})

    def _get_int_value(self, settings, name):
        # Convierte el valor del parámetro a entero.
        setting = self._get_setting(settings, name)

        try:
            return int(setting.get("setting"))
        except (TypeError, ValueError):
            return None

    def _get_unit(self, settings, name):
        # Obtiene la unidad del parámetro.
        setting = self._get_setting(settings, name)
        return setting.get("unit", "")

    def _setting_to_mb(self, settings, name):
        # Convierte valores de memoria a MB.
        value = self._get_int_value(settings, name)
        unit = self._get_unit(settings, name)

        if value is None:
            return None

        if unit == "8kB":
            return value * 8 / 1024

        if unit == "kB":
            return value / 1024

        if unit == "MB":
            return value

        if unit == "GB":
            return value * 1024

        return value

    def _check_shared_buffers(self, settings):
        # Revisa SHOW shared_buffers;
        issues = []

        shared_buffers_mb = self._setting_to_mb(settings, "shared_buffers")

        if shared_buffers_mb is not None and shared_buffers_mb < 256:
            issues.append(
                self._add_issue(
                    code="CFG001",
                    level="medium",
                    title="shared_buffers posiblemente demasiado bajo",
                    desc=(
                        f"shared_buffers está configurado en aproximadamente "
                        f"{shared_buffers_mb:.0f} MB. "
                        "Un valor bajo puede limitar la caché interna de PostgreSQL."
                    ),
                    table="",
                    sql_check="SHOW shared_buffers;",
                    sql_fix=(
                        "-- Revisar shared_buffers en postgresql.conf.\n"
                        "-- Sugerencia: ajustarlo según la memoria disponible del servidor."
                    ),
                )
            )

        return issues

    def _check_work_mem(self, settings):
        # Revisa SHOW work_mem;
        issues = []

        work_mem_mb = self._setting_to_mb(settings, "work_mem")

        if work_mem_mb is not None and work_mem_mb < 4:
            issues.append(
                self._add_issue(
                    code="CFG002",
                    level="low",
                    title="work_mem posiblemente bajo",
                    desc=(
                        f"work_mem está configurado en aproximadamente "
                        f"{work_mem_mb:.0f} MB. "
                        "Un valor bajo puede hacer que ordenamientos o joins usen disco."
                    ),
                    table="",
                    sql_check="SHOW work_mem;",
                    sql_fix=(
                        "-- Revisar work_mem en postgresql.conf.\n"
                        "-- Sugerencia: aumentarlo con cuidado porque aplica por operación."
                    ),
                )
            )

        return issues

    def _check_pg_stat_statements_max(self, settings):
        # Revisa SHOW pg_stat_statements.max;
        issues = []

        pg_stat_statements_max = self._get_int_value(
            settings,
            "pg_stat_statements.max"
        )

        if pg_stat_statements_max is None:
            issues.append(
                self._add_issue(
                    code="CFG003",
                    level="medium",
                    title="pg_stat_statements.max no disponible",
                    desc=(
                        "No se encontró pg_stat_statements.max en el snapshot. "
                        "Puede indicar que pg_stat_statements no está habilitado."
                    ),
                    table="",
                    sql_check="SHOW pg_stat_statements.max;",
                    sql_fix=(
                        "-- Revisar que pg_stat_statements esté cargado.\n"
                        "-- En clase se vio con shared_preload_libraries."
                    ),
                )
            )
            return issues

        if pg_stat_statements_max < 10000:
            issues.append(
                self._add_issue(
                    code="CFG004",
                    level="medium",
                    title="pg_stat_statements.max posiblemente bajo",
                    desc=(
                        f"pg_stat_statements.max está configurado en "
                        f"{pg_stat_statements_max}. "
                        "Un valor bajo puede limitar el historial de consultas monitoreadas."
                    ),
                    table="",
                    sql_check="SHOW pg_stat_statements.max;",
                    sql_fix=(
                        "-- Revisar pg_stat_statements.max en postgresql.conf.\n"
                        "-- En clase se usó como referencia: pg_stat_statements.max = 10000."
                    ),
                )
            )

        return issues

    def _check_log_min_duration_statement(self, settings):
        # Revisa SHOW log_min_duration_statement;
        issues = []

        log_min_duration = self._get_int_value(
            settings,
            "log_min_duration_statement"
        )

        if log_min_duration is None:
            issues.append(
                self._add_issue(
                    code="CFG005",
                    level="medium",
                    title="log_min_duration_statement no disponible",
                    desc=(
                        "No se encontró log_min_duration_statement en el snapshot. "
                        "No se puede verificar si PostgreSQL registra consultas lentas."
                    ),
                    table="",
                    sql_check="SHOW log_min_duration_statement;",
                    sql_fix=(
                        "-- Revisar log_min_duration_statement en postgresql.conf."
                    ),
                )
            )
            return issues

        # En PostgreSQL, -1 significa que no registra consultas lentas.
        if log_min_duration == -1:
            issues.append(
                self._add_issue(
                    code="CFG006",
                    level="medium",
                    title="Registro de consultas lentas desactivado",
                    desc=(
                        "log_min_duration_statement está en -1. "
                        "PostgreSQL no está registrando consultas lentas."
                    ),
                    table="",
                    sql_check="SHOW log_min_duration_statement;",
                    sql_fix=(
                        "-- Activar registro de consultas lentas.\n"
                        "-- En clase se usó como referencia: log_min_duration_statement = 500."
                    ),
                )
            )

        elif log_min_duration > 500:
            issues.append(
                self._add_issue(
                    code="CFG007",
                    level="low",
                    title="Umbral de consultas lentas posiblemente alto",
                    desc=(
                        f"log_min_duration_statement está configurado en "
                        f"{log_min_duration} ms. "
                        "Un umbral alto puede ocultar consultas lentas relevantes."
                    ),
                    table="",
                    sql_check="SHOW log_min_duration_statement;",
                    sql_fix=(
                        "-- Considerar un umbral menor para detectar queries lentas.\n"
                        "-- En clase se usó como referencia: 500 ms."
                    ),
                )
            )

        return issues