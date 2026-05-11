from app.connector.snapshot import take_snapshot
from app.connector.pg_client import db

def verify_system():
    print("Pruebas de PgGuardian")
    
    try:
        #Probar Conexión 
        print("\nVerifican conexión física")
        conn = db.connect_to_target()
        if conn and not conn.closed:
            print("Conexión establecida con bd Cliente (TiendaDB).")
        else:
            print("Error: No se pudo abrir la conexión.")
            return

        # Probar Snapshots
        print("\nGenerando Snapshots")
        snapshot = take_snapshot()
        print("Snapshot capturado")

        # Validar datos
        print("\nValidando datos:")
        
        # Verificar tablas
        table_count = len(snapshot.tables)
        print(f"Tablas detectadas: {table_count}")
        
        # Verificar configuración
        shared_buffers = next((item for item in snapshot.settings if item['name'] == 'shared_buffers'), None)
        if shared_buffers:
            print(f"Configuración: shared_buffers = {shared_buffers['setting']} {shared_buffers['unit'] or ''}")

        # Verificar sesiones
        print(f"Sesiones activas capturadas: {len(snapshot.connections)}")

        print("\nEl sistema de extracción funciona correctamente. ---")

    except Exception as e:
        print(f"\nError durante la prueba: {e}")
    finally:
        db.close_all()

if __name__ == "__main__":
    verify_system()