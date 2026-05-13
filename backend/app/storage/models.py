from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os
import datetime

# Base para el mapeo de SQLAlchemy
Base = declarative_base()

class SnapshotRecord(Base):

    # Esta tabla registra cada sesión de auditoría. Nos sirve para mantener un historial de salud de la base de datos a través del tiempo.
    __tablename__ = 'snapshots'
    
    id = Column(Integer, primary_key=True)
    taken_at = Column(DateTime, default=datetime.datetime.utcnow) 
    db_name = Column(String, nullable=False) 
    db_host = Column(String, nullable=False)
    
    findings = relationship("Finding", back_populates="snapshot", cascade="all, delete-orphan")

class Finding(Base):

    # Aquí se centralizan todos los problemas que detectan los módulos de índices y salud.

    __tablename__ = 'findings'
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('snapshots.id'))
    
    # Identificadores internos para seguimiento
    problem_code = Column(String)   
    category = Column(String)       
    severity = Column(String)
    is_resolved = Column(Boolean, default=False) 
    detected_at = Column(DateTime, default=datetime.datetime.utcnow) 
           
    # Información descriptiva para el usuario final
    title = Column(String)
    description = Column(Text)
    table_name = Column(String)     # Tabla específica donde vive el problema
    
    # Bloques de código SQL para la sección de evidencia y solución técnica
    evidence_sql = Column(Text)     # El query que demuestra que el error existe
    fix_sql = Column(Text)          # El comando SQL para solucionar el problema directamente

    snapshot = relationship("SnapshotRecord", back_populates="findings")

#tabla para guardar los reportes
class Report(Base):
    # tabla para info del Dashboard y el PDF.
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('snapshots.id'))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    report_path = Column(String)  # Ruta del PDF generado

    total_high = Column(Integer, default=0)
    total_medium = Column(Integer, default=0)
    total_low = Column(Integer, default=0)

    # Relación con el snapshot
    snapshot = relationship("SnapshotRecord")

#  conexión a PgGuardianDB
engine = create_engine(os.getenv("OWN_DB_URI"))

# sesiones
SessionLocal = sessionmaker(bind=engine)

def get_session():
    return SessionLocal()