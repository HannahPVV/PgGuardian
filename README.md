# PgGuardian
PgGuardian es una plataforma full stack de auditoría para PostgreSQL que analiza la salud de bases de datos, detecta problemas de rendimiento y configuración, almacena snapshots históricos y genera reportes accionables.

El objetivo de PgGuardian es ayudar a equipos que usan PostgreSQL y que no cuentan con un DBA dedicado. La herramienta revisa información interna de PostgreSQL para detectar posibles problemas antes de que afecten el rendimiento de la aplicación.

PgGuardian trabaja en modo de análisis. Su propósito principal es observar, detectar y recomendar, no modificar automáticamente la base de datos auditada.

Requisitos previos

Antes de ejecutar el proyecto, asegúrate de tener instalado:

- Docker Desktop.
- Git.
- Navegador web.
- Visual Studio Code, opcional pero recomendado.

Para comprobar que Docker está instalado, ejecuta:
docker --version

Para comprobar que Docker Compose está instalado, ejecuta:
docker compose version

Instalación dle proyecto

1. Clonar el repositorio
Si todavía no tienes el proyecto en tu computadora, ejecuta:
git clone https://github.com/HannahPVV/PgGuardian.git
cd PgGuardian

Entra a la ruta correspondiente. En Windows, por ejemplo:
cd C:\PgGuardian

Ejecución con Docker Compose

1. Verificar que Docker Desktop esté abierto:
docker ps

2. Levantar el proyecto
Desde la raíz del proyecto, ejecuta:
docker compose up --build

3. Abrir la aplicación en el navegador:
http://localhost:5001


Problemas comunes y soluciones

1. Docker Desktop no está abierto
- Ejecuta: docker compose down
- Abrir Docker Desktop.
- Esperar a que termine de iniciar.
- Ejecutar: docker ps
V- olver a levantar el proyecto:
docker compose up --build

2. Error de puerto 5434 está ocupado
- Ejecuta: docker compose down
- Para revisar los contenedores activos, ejecuta:
docker ps
- Ejemplo: el puerto esta ocupado por una base de datos llamada proyecto-db.
- Para detener ese contenedor, ejecuta:
docker stop proyecto-db
- Después vuelve a levantar el proyecto:
docker compose up --build




