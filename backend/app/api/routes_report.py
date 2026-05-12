from fastapi import APIRouter, HTTPException
from storage.models import SnapshotRecord, Finding, Report, get_session

router = APIRouter()

@router.get("/snapshots")
def get_snapshots():
    session = get_session()
    try:
        # Ordenar por los más recientes primero
        snapshots = session.query(SnapshotRecord).order_by(
            SnapshotRecord.taken_at.desc()
        ).all()
        return [
            {
                "id": s.id,
                "db_name": s.db_name,
                "db_host": s.db_host,
                "taken_at": s.taken_at
            }
            for s in snapshots
        ]
    finally:
        session.close()

@router.get("/report/{snapshot_id}")
def get_report(snapshot_id: int):
    session = get_session()
    try:
        # Hallazgos ordenados por severity
        findings = session.query(Finding).filter(
            Finding.snapshot_id == snapshot_id
        ).order_by(Finding.severity.desc()).all()

        if not findings:
            raise HTTPException(status_code=404, detail="No se encontraron hallazgos para este snapshot")

        return [
            {
                "id": f.id,
                "problem_code": f.problem_code,
                "category": f.category,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "table_name": f.table_name,
                "evidence_sql": f.evidence_sql,
                "fix_sql": f.fix_sql,
                "detected_at": f.detected_at
            }
            for f in findings
        ]
    finally:
        session.close()

@router.get("/summary/{snapshot_id}")
def get_summary(snapshot_id: int):
    session = get_session()
    try:
        # Este sirve para las gráficas del Dashboard (High, Medium, Low)
        report = session.query(Report).filter(
            Report.snapshot_id == snapshot_id
        ).first()

        if not report:
            raise HTTPException(status_code=404, detail="Resumen no encontrado")

        return {
            "snapshot_id": snapshot_id,
            "total_high": report.total_high,
            "total_medium": report.total_medium,
            "total_low": report.total_low,
            "created_at": report.created_at
        }
    finally:
        session.close()