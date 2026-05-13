from fastapi import APIRouter, HTTPException
from connector.snapshot import take_snapshot 
from storage.models import SnapshotRecord, Finding, Report, get_session
from detectors.registry import registry
import os

router = APIRouter()

@router.post("/snapshot")
def run_snapshot():
    # Ahora es una función directa, no instanciamos clase
    try:
        snapshot_obj = take_snapshot()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al conectar con TiendaDB: {str(e)}")

    findings = registry.run_all(snapshot_obj)

    session = get_session()
    try:
        snap_record = SnapshotRecord(
            db_name=os.getenv("TARGET_DB_NAME", "tiendadb"),
            db_host=os.getenv("TARGET_DB_HOST", "db")
        )
        session.add(snap_record)
        session.flush() 

        for f in findings:
            session.add(Finding(
                snapshot_id=snap_record.id,
                problem_code=f["problem_code"],
                category=f["category"],
                severity=f["severity"],
                title=f["title"],
                description=f["description"],
                table_name=f["table_name"],
                evidence_sql=f["evidence_sql"],
                fix_sql=f["fix_sql"]
            ))

        #  Numeor de hallazgos por severidad para el Reporte
        t_high = sum(1 for f in findings if f["severity"] == "high")
        t_medium = sum(1 for f in findings if f["severity"] == "medium")
        t_low = sum(1 for f in findings if f["severity"] == "low")

        session.add(Report(
            snapshot_id=snap_record.id,
            total_high=t_high,
            total_medium=t_medium,
            total_low=t_low
        ))
        
        session.commit()
        return {"status": "success", "snapshot_id": snap_record.id, "total": len(findings)}

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar: {str(e)}")
    finally:
        session.close()