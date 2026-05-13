from storage.models import SnapshotRecord, Finding

class SnapshotComparator:
    def __init__(self, session):
        self.session = session

    def compare(self, current_snap_id):
        
        #Compara los hallazgos del snapshot actual contra el anterior.
        # Retorna un resumen de qué es nuevo y qué se solucionó.

        # 1. Buscamos el snapshot actual
        current_snap = self.session.query(SnapshotRecord).get(current_snap_id)
        if not current_snap:
            return None

        # 2. Buscamos el snapshot anterior de la misma base de datos
        previous_snap = self.session.query(SnapshotRecord)\
            .filter(SnapshotRecord.id < current_snap_id, 
                    SnapshotRecord.db_name == current_snap.db_name)\
            .order_by(SnapshotRecord.id.desc())\
            .first()

        if not previous_snap:
            return {
                "status": "first_run",
                "message": "Primera auditoría realizada. No hay historial para comparar.",
                "new_count": len(current_snap.findings),
                "fixed_count": 0
            }

        # 3. Lógica de comparación de códigos de error
        current_codes = {f.problem_code for f in current_snap.findings}
        previous_codes = {f.problem_code for f in previous_snap.findings}

        new_issues = current_codes - previous_codes
        fixed_issues = previous_codes - current_codes

        return {
            "status": "compared",
            "timestamp": current_snap.taken_at,
            "previous_timestamp": previous_snap.taken_at,
            "new_count": len(new_issues),
            "fixed_count": len(fixed_issues),
            "summary": f"Se encontraron {len(new_issues)} problemas nuevos y se solucionaron {len(fixed_issues)} desde la última revisión."
        }