from fastapi import FastAPI

# Esta es la línea que le falta a tu código o que tiene un nombre distinto
app = FastAPI() 

@app.get("/")
def home():
    return {"message": "Hola desde PgGuardian"}