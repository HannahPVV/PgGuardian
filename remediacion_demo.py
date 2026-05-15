import psycopg2
from psycopg2 import extensions

def corregir_db():
    db_uri = "postgresql://tienda_user:tienda_pass@localhost:5435/tiendadb"
    
    print(" Aplicando correcciones detectadas en el Dashboard...")
    conn = None
    try:
        conn = psycopg2.connect(db_uri)
        conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # 1. Resolvemos IDX003 (Índice duplicado)
        print("- Eliminando idx_products_sku (Hallazgo IDX003)...")
        cur.execute("DROP INDEX IF EXISTS idx_products_sku;")
        
        # 2. Resolvemos IDX004 (Índice parcial faltante)
        print("- Creando idx_customers_country_part (Hallazgo IDX004)...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_customers_country_part 
            ON customers(country) WHERE country != 'MX';
        """)

        print("\n ¡Remediación completada exitosamente!")
        print(" Paso final: Haz clic en 'ESCANEAR BASE DE DATOS' en el Dashboard.")
        
    except Exception as e:
        print(f"\n Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    corregir_db()