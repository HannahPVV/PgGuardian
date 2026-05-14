import os
import requests
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="PgGuardian Frontend")
base_path = os.path.dirname(os.path.abspath(__file__))

# Configuración de carpetas
templates = Jinja2Templates(directory=os.path.join(base_path, "templates"))

if os.path.exists(os.path.join(base_path, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(base_path, "static")), name="static")

API_BASE_URL = "http://localhost:8000/api"

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
async def compare(request: Request, base_id: int = None, actual_id: int = None):
    # Forzamos a que la lista empiece vacía
    lista_final = []
    mejora, resueltos, ahorro = 0, 0, 0
    
    try:
        
        print("Intentando conectar al API...")
        response = requests.get(f"{API_BASE_URL}/snapshots")
        
        if response.status_code == 200:
            lista_final = response.json()
            # ESTO DEBE SALIR EN LA TERMINAL:
            print(f"ÉXITO: Se cargaron {len(lista_final)} snapshots")
        else:
            print(f"ERROR: El API respondió con código {response.status_code}")

     
        if base_id and actual_id:
            data_1 = requests.get(f"{API_BASE_URL}/summary/{base_id}").json()
            data_2 = requests.get(f"{API_BASE_URL}/summary/{actual_id}").json()
            
            # Sumamos hallazgos para comparar
            total_1 = data_1.get('total_high', 0) + data_1.get('total_medium', 0)
            total_2 = data_2.get('total_high', 0) + data_2.get('total_medium', 0)
            
            resueltos = max(0, total_1 - total_2)
            mejora = 100 if total_2 == 0 else min(100, int((resueltos / total_1) * 100)) if total_1 > 0 else 0
            ahorro = resueltos * 150

    except Exception as e:
        print(f"HUBO UN PROBLEMA: {e}")

    
    return templates.TemplateResponse("compare.html", {
        "request": request,
        "snapshots": lista_final, 
        "id_base": base_id,
        "id_actual": actual_id,
        "puntos_mejorados": mejora,
        "resueltos": resueltos,
        "ahorro": ahorro
    })


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)