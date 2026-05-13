import logging
from connector.snapshot import take_snapshot
from detectors.registry import registry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestMotor")

def test_pgguardian_motor():
    logger.info("--- INICIANDO PRUEBA FUNCIONAL DE PGGUARDIAN ---")
    
    try:
        logger.info("Capturando estado de la base de datos (Snapshot)...")
        snap = take_snapshot()
        
        hallazgos = registry.run_all(snap)
        
        print("\n" + "="*60)
        print(f" {'REPORT DE AUDITORÍA TÉCNICA':^58}")
        print("="*60)
        print(f"Total de problemas detectados: {len(hallazgos)}")
        print("-"*60)
        
        for h in hallazgos:
            nivel = (h.get('level') or h.get('severity') or 'info').upper()
            titulo = h.get('title', 'Sin título')
            codigo = h.get('code') or h.get('id') or 'GEN-001'
            
            prefix = f"[{nivel}]"
            print(f"{prefix:10} {codigo}: {titulo}")
            
        print("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Error crítico durante la prueba: {e}")

    logger.info("--- PRUEBA FINALIZADA ---")

if __name__ == "__main__":
    test_pgguardian_motor()