import os
import psycopg2
import psycopg2.extras
from psycopg2 import extensions
from dotenv import load_dotenv
import logging


# Carga las variables de .env 
load_dotenv()

# Configura Logs 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PgGuardian-Internal")

class PgGuardianConnector:
    """
    Abre, mantiene y cierra la conexión hacia las BD TiendaDB y PgGuardianDB
    """
    def __init__(self):
        self.target_uri = os.getenv("TARGET_DB_URI")
        self.own_uri = os.getenv("OWN_DB_URI")
        
        # variables para guardar conexión activa una vez que se abra
        self._target_conn = None
        self._own_conn = None

    def connect_to_target(self):
        """
        Abrir conexión con la base de datos TiendaDB.
        """
        # Si la conexión no existe o se cerró, intenta abrir una nueva
        if self._target_conn is None or self._target_conn.closed:
            try:
                self._target_conn = psycopg2.connect(
                    self.target_uri, 
                    # config read only en TiendaBD
                    options="-c default_transaction_read_only=on",
                    connect_timeout=5
                )
                # Configuración de la conexión
                self._target_conn.autocommit = True
                self._target_conn.set_session(readonly=True)

                logger.info("Conexión establecida con la base de datos a auditar.")
            except psycopg2.Error as e:
                logger.error(f"No se pudo conectar a la BD: {e.pgerror}")
                return None
        return self._target_conn
    
    def connect_to_own(self):
        """
        Establece conexión con base de datos para guardar resultados (PgGuardianDB)
        """
        if self._own_conn is None or self._own_conn.closed:
            try:
                # Conexión 
                self._own_conn = psycopg2.connect(self.own_uri)
                logger.info("Conexión establecida con PgGuardianDB.")
            except psycopg2.Error as e:
                logger.error(f"Error al conectar con PgGuardianDB: {e.pgerror}")
                return None
        return self._own_conn

    def run_query(self, conn, sql_query, params=None):
        """
        Manda query a la base de datos y trae la respuesta.
        """
        if conn is None:
            return []
        try:
            # RealDictCursor trae la respuesta en un diccionario 
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql_query, params or ())
                # Si la consulta trae filas, las regresa todas
                if cur.description:
                    return cur.fetchall()
                return []
        except psycopg2.Error as e:
            logger.warning(f"Error al ejecutar la consulta: {e.pgerror}")
            return []

    def close_all(self):
        """
        Cierra todas las conexiones.
        """
        if self._target_conn: self._target_conn.close()
        if self._own_conn: self._own_conn.close()
        logger.info("Conexiones cerradas.")

# Creamos un objeto
db = PgGuardianConnector()

# Interfaz para  Snapshot
class DBAuditInterface:
    def execute_query(self, sql):
        # Verificar que la conexión esté activa para ejecutar la consulta
        conn = db.connect_to_target()
        # ejecucción de la consulta y retorno del resultado
        return db.run_query(conn, sql)

# objeto para usar en snapshot.py y poder ejecutar las consultas
db_client = DBAuditInterface()
