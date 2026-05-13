import logging

from .indexes import ForeignKeyIndexDetector, UnusedIndexesDetector, DuplicateIndexesDetector
from .health import IdleInTransactionDetector, ActiveLocksDetector, ConnectionSpikeDetector
from .queries import TopQueriesDetector

# Configuración básica para ver qué está pasando en la terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PgGuardian_Registry")

class DetectorRegistry:
    def __init__(self):
        
        #Aquí se registran todos los módulos.
        self._detectors = [
            ForeignKeyIndexDetector(),
            UnusedIndexesDetector(),
            DuplicateIndexesDetector(),
            IdleInTransactionDetector(),
            ActiveLocksDetector(),
            ConnectionSpikeDetector(),
            TopQueriesDetector(),
        ]

    def run_all(self, snap_object):
        
        #Este es el motor: corre todos los detectores uno por uno y 
        #junta los resultados para que luego los guardemos en la DB.

        all_issues = []
        
        logger.info("Iniciando revisión técnica...")
        
        for detector in self._detectors:
            try:
                logger.info(f"Ejecutando: {detector.__class__.__name__}")
                results = detector.run(snap_object)
                
                if results:
                    all_issues.extend(results)
                    
            except Exception as e:
                # Si un detector falla, el programa sigue con los demás
                logger.error(f"Error en el módulo {detector.__class__.__name__}: {str(e)}")
        
        logger.info(f"Revisión terminada. Hallazgos totales: {len(all_issues)}")
        return all_issues

# Creamos la instancia global
registry = DetectorRegistry()