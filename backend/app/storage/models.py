from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
import datetime

# Base para el mapeo de SQLAlchemy
Base = declarative_base()

class SnapshotRecord(Base):

    # Esta tabla registra cada sesión de auditoría. Nos sirve para mantener un historial de salud de la base de datos a través del tiempo.
    __tablename__ = 'snapshot_records'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow) 
    db_name = Column(String) 
    
    findings = relationship("Finding", back_populates="snapshot", cascade="all, delete-orphan")

class Finding(Base):

    # Aquí se centralizan todos los problemas que detectan los módulos de índices y salud.

    __tablename__ = 'findings'
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('snapshot_records.id'))
    
    # Identificadores internos para seguimiento
    problem_code = Column(String)   
    category = Column(String)       
    severity = Column(String)       
    
    # Información descriptiva para el usuario final
    title = Column(String)
    description = Column(Text)
    table_name = Column(String)     # Tabla específica donde vive el problema
    
    # Bloques de código SQL para la sección de evidencia y solución técnica
    evidence_sql = Column(Text)     # El query que demuestra que el error existe
    fix_sql = Column(Text)          # El comando SQL para solucionar el problema directamente

    snapshot = relationship("SnapshotRecord", back_populates="findings")
