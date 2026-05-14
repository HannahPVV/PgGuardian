from fastapi import APIRouter, HTTPException, BackgroundTasks # Agregamos BackgroundTasks
from fastapi.responses import FileResponse
from storage.models import Finding, SnapshotRecord, Report, get_session # Agregamos 'Report'
from utils.report_generator import ReportGenerator
import os

router = APIRouter()

@router.get("/generate-report/{snapshot_id}")
def export_pdf(snapshot_id: int, background_tasks: BackgroundTasks): 
    session = get_session()
    try:
        folder = "reportes"
        if not os.path.exists(folder):
            os.makedirs(folder)

        file_path = os.path.join(folder, f"reporte_{snapshot_id}.pdf")
        # buscar snapshot
        snap_record = session.query(SnapshotRecord).filter(SnapshotRecord.id == snapshot_id).first()
        if not snap_record:
            raise HTTPException(status_code=404, detail="Snapshot no encontrado")
        
        # hallar hallazgos relacionados al snapshot
        findings = session.query(Finding).filter(Finding.snapshot_id == snapshot_id).all()

        hallazgos_para_pdf = [
            {
                "problem_code": f.problem_code,
                "title": f.title,
                "description": f.description,
                "table_name": f.table_name,
                "fix_sql": f.fix_sql,
                "severity": f.severity
            } for f in findings
        ]

        # generar PDF
        generator = ReportGenerator(hallazgos_para_pdf)
        file_path = os.path.join(folder, f"reporte_{snapshot_id}.pdf")  
        generator.create_pdf(file_path)

        # actualizar ruta del reporte en la base de datos
        report_entry = session.query(Report).filter(Report.snapshot_id == snapshot_id).first()
        if report_entry:
            report_entry.report_path = file_path
            session.commit()
   
        # Esto borra el archivo del servidor DESPUÉS de que el usuario lo descarga
        background_tasks.add_task(os.remove, file_path) 

        return FileResponse(
            path=file_path, 
            filename=f"Auditoria_{snap_record.db_name}.pdf",
            media_type='application/pdf'
        )
        
    except Exception as e:
        session.rollback() # Por si falla el commit
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Error interno al generar PDF")
    finally:
        session.close()