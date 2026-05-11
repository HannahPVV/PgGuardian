from abc import ABC, abstractmethod
from app.connector.snapshot import Snapshot

class Detector(ABC):
    #Clase base para los detectores
    
    # Categoría modificar en cada detector específico para organizar los resultados en el frontend
    category = " "

    @abstractmethod
    def run(self, snap: Snapshot):
        #aquí se debe poner la lógica de detección de errores en los detectores específicos, usando la información del snapshot
        pass

    def _add_issue(self, code, level, title, desc, table="", sql_check="", sql_fix=""):
        # estadarización de resultados de los detectores con la base de datos y frontend 
        return {
            "problem_code": code,
            "category":     self.category, # aqui se usa la categoría definda al principio de la clase
            "severity":     level, # low, medium, high
            "title":        title,
            "description":  desc,
            "table_name":   table,
            "evidence_sql": sql_check,
            "fix_sql":      sql_fix
        }