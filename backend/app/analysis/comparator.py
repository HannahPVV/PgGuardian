from storage.models import SnapshotRecord, Finding

class SnapshotComparator:
    def __init__(self, session):
        self.session = session

    def _fingerprint(self, finding):
        return (finding.problem_code, finding.table_name or "")

    def compare(self, base_snap_id, current_snap_id):
        # Buscamos los dos snapshots
        previous_snap = self.session.query(SnapshotRecord).get(base_snap_id)
        current_snap = self.session.query(SnapshotRecord).get(current_snap_id)
        
        if not previous_snap or not current_snap:
            return None #  si los IDs no existen

        
        current_fps = {self._fingerprint(f): f for f in current_snap.findings}
        previous_fps = {self._fingerprint(f): f for f in previous_snap.findings}

        fixed_keys = set(previous_fps) - set(current_fps)
        new_keys = set(current_fps) - set(previous_fps)
        persistent_keys = set(current_fps) & set(previous_fps)

        def serialize(f):
            return {
                "problem_code": f.problem_code,
                "table_name": f.table_name,
                "title": f.title,
                "severity": f.severity,
                "description": getattr(f, 'description', 'Sin descripción')
            }

        hallazgos_solucionados = [serialize(previous_fps[fp]) for fp in fixed_keys]

        return {
            "status": "compared",
            "timestamp": current_snap.taken_at,
            "previous_timestamp": previous_snap.at if hasattr(previous_snap, 'at') else None,
            "new_count": len(new_keys),
            "fixed_count": len(fixed_keys),
            "summary": f"Se solucionaron {len(fixed_keys)} problemas.",
            "hallazgos_solucionados": hallazgos_solucionados
        }