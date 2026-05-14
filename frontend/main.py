import os
import requests
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional 

app = FastAPI(title="PgGuardian Frontend")
base_path = os.path.dirname(os.path.abspath(__file__))

# Configuración de carpetas
templates = Jinja2Templates(directory=os.path.join(base_path, "templates"))

if os.path.exists(os.path.join(base_path, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(base_path, "static")), name="static")


API_BASE_URL = "http://pgguardian_backend:8000/api"

def get_latest_snapshot_id():
    try:
        res = requests.get(f"{API_BASE_URL}/snapshots")
        if res.status_code == 200:
            data = res.json()
            if len(data) > 0:
                return data[0]["id"]
    except Exception as e:
        print(f"Error conectando con el backend: {e}")
    return None

@app.get("/")
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    total, uniques, salud = 0, 0, 100
    db_name = "Esperando conexión..." 
    
    snap_id = get_latest_snapshot_id()
    
    if snap_id:
        try:
            # 1. Obtenemos detalles del snapshot
            res_snapshots = requests.get(f"{API_BASE_URL}/snapshots")
            if res_snapshots.status_code == 200:
                latest_snap = res_snapshots.json()[0]
                db_name = latest_snap.get("db_name", "TiendaDB")

            # 2. Calculamos salud
            res_summary = requests.get(f"{API_BASE_URL}/summary/{snap_id}")
            if res_summary.status_code == 200:
                data = res_summary.json()
                total = data["total_high"] + data["total_medium"] + data["total_low"]
                castigo = (data["total_high"] * 10) + (data["total_medium"] * 5) + (data["total_low"] * 2)
                salud = max(5, 100 - castigo)
            
            # 3. Calculamos tipos de problemas
            res_report = requests.get(f"{API_BASE_URL}/report/{snap_id}")
            if res_report.status_code == 200:
                findings = res_report.json()
                codigos = set(f.get("problem_code", "GEN") for f in findings)
                uniques = len(codigos)

        except Exception as e:
            print(f"Error cargando dashboard: {e}")


    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "total_findings": total, 
        "unique_types": uniques, 
        "health_score": salud,
        "db_name": db_name
    })

@app.get("/report", response_class=HTMLResponse)
async def report(request: Request):
    findings = []
    snap_id = get_latest_snapshot_id()
    if snap_id:
        try:
            res = requests.get(f"{API_BASE_URL}/report/{snap_id}")
            if res.status_code == 200:
                findings = res.json()
        except Exception as e:
            print(f"Error cargando reportes: {e}")
            
    return templates.TemplateResponse("report.html", {
        "request": request,
        "findings": findings
    })


@app.get("/compare", response_class=HTMLResponse)
async def compare(request: Request, base_id: Optional[str] = None, actual_id: Optional[str] = None):
    lista_final = []
    mejora, resueltos, ahorro = 0, 0, 0
    
    # 1. Convertimos a entero de forma segura
    b_id = int(base_id) if base_id and base_id.isdigit() else None
    a_id = int(actual_id) if actual_id and actual_id.isdigit() else None
    
    try:
        # 2. Siempre cargamos la lista para los selectores del HTML
        response = requests.get(f"{API_BASE_URL}/snapshots")
        if response.status_code == 200:
            lista_final = response.json()
        
        # 3. Solo si tenemos ambos IDs calculamos la comparación
        if b_id and a_id:
            # Pedimos los resúmenes al backend usando los IDs numéricos
            res_1 = requests.get(f"{API_BASE_URL}/summary/{b_id}")
            res_2 = requests.get(f"{API_BASE_URL}/summary/{a_id}")
            
            if res_1.status_code == 200 and res_2.status_code == 200:
                data_1 = res_1.json()
                data_2 = res_2.json()
                
                # Sumamos hallazgos (Críticos + Medios)
                total_1 = data_1.get('total_high', 0) + data_1.get('total_medium', 0)
                total_2 = data_2.get('total_high', 0) + data_2.get('total_medium', 0)
                
                # Lógica de mejora
                resueltos = max(0, total_1 - total_2)
                if total_1 > 0:
                    mejora = min(100, int((resueltos / total_1) * 100))
                elif total_1 == 0 and total_2 == 0:
                    mejora = 0 # No hay problemas, no hay mejora que medir
                
                ahorro = resueltos * 150 # Dato ficticio para el KPI
                print(f"Comparación exitosa: {b_id} vs {a_id}")

    except Exception as e:
        print(f"HUBO UN PROBLEMA EN COMPARE: {e}")

    # 4. Retornamos al template (pasamos los IDs originales para que el HTML sepa cuál seleccionar)
    return templates.TemplateResponse("compare.html", {
        "request": request,
        "snapshots": lista_final, 
        "id_base": b_id,
        "id_actual": a_id,
        "puntos_mejorados": mejora,
        "resueltos": resueltos,
        "ahorro": ahorro
    })
    
    return templates.TemplateResponse("compare.html", {
        "request": request,
        "snapshots": lista_final, 
        "id_base": base_id,
        "id_actual": actual_id,
        "puntos_mejorados": mejora,
        "resueltos": resueltos,
        "ahorro": ahorro
    })

@app.post("/run-audit")
async def run_audit():
    try:
        # Le pedimos al backend real que haga el snapshot
        response = requests.post(f"{API_BASE_URL}/snapshot")
        if response.status_code == 200:
            return {"status": "success", "snapshot_id": response.json().get("id")}
        return {"status": "error", "message": "No se pudo crear el snapshot"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/download-report/{snapshot_id}")
async def download_report(snapshot_id: str):
    # 1. Validación de seguridad para evitar el error "None"
    if snapshot_id == "None" or not snapshot_id:
        return {"status": "error", "message": "Por favor, selecciona un snapshot primero."}

    try:
        # 2. Llamamos al backend pasando el ID dinámico
        # Usamos stream=True para manejar el archivo de forma eficiente
        backend_url = f"{API_BASE_URL}/generate-report/{snapshot_id}"
        response = requests.get(backend_url, stream=True)
        
        if response.status_code == 200:
            # 3. Reenviamos el contenido del PDF al navegador del usuario
            # Usamos StreamingResponse para que la descarga sea fluida
            return StreamingResponse(
                response.iter_content(chunk_size=4096),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=Auditoria_PgGuardian_{snapshot_id}.pdf"
                }
            )
        else:
            # Si el backend falla, devolvemos el error que mande el back
            return {"status": "error", "message": f"El backend falló con código: {response.status_code}"}
            
    except Exception as e:
        # Error si el backend está apagado o no hay red
        return {"status": "error", "message": f"Error de conexión con el servidor: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)