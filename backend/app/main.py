from fastapi import FastAPI
# Importamos routers 
from api.routes_snapshot import router as snapshot_router
from api.routes_report import router as report_router
from api.routes_export import router as export_router

app = FastAPI(title="PgGuardian")

# Registramos el router de snapshots
# endpoint POST para ejecutar auditoría y guardar resultados
app.include_router(snapshot_router, prefix="/api", tags=["Audit"])
# endpoint GET para reportes e historial
app.include_router(report_router, prefix="/api", tags=["History"])

app.include_router(export_router, prefix="/api", tags=["Export"])



@app.get("/")
def home():
    return {
        "message": "Hola desde PgGuardian"
    }