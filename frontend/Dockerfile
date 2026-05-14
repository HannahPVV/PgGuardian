FROM python:3.11-slim

# Mismas dependencias porque también usas Python/FastAPI
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Aquí se instalarán requests y jinja2 que necesita tu front
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código del dashboard (asegúrate de que las carpetas templates y static estén aquí)
COPY . .

# CAMBIO: Usamos el 5001 para que la API se quede con el 8000
EXPOSE 5001

# Ejecutamos el archivo del front (si tu archivo se llama main.py)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001", "--reload"]