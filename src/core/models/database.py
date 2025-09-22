"""
Modelos de banco de dados usando SQLAlchemy
Define as tabelas para transações, usuários e alertas
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Configurar banco SQLite
DATABASE_URL = "sqlite:///./financeiro.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    """Modelo para usuários do sistema"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Transaction(Base):
    """Modelo para transações financeiras"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    raw_message = Column(Text, nullable=False)
    
    # Dados extraídos pelo ExtratorFinanceiro
    transaction_type = Column(String, nullable=False)  # gasto, receita, transferencia
    amount = Column(Float, nullable=True)
    currency = Column(String, default="BRL")
    category = Column(String, nullable=True)
    place = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    transaction_date = Column(DateTime, nullable=True)
    
    # Metadados
    confidence = Column(Float, nullable=True)
    extraction_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

class Alert(Base):
    """Modelo para alertas e configurações"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    alert_type = Column(String, nullable=False)  # category_limit, total_balance, etc
    
    # Configurações do alerta
    category = Column(String, nullable=True)  # Para alertas por categoria
    limit_amount = Column(Float, nullable=True)
    period = Column(String, default="month")  # month, week, day
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AlertHistory(Base):
    """Histórico de alertas disparados"""
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    alert_id = Column(Integer, nullable=True)
    message = Column(Text, nullable=False)
    alert_type = Column(String, nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    
    # Dados que dispararam o alerta
    trigger_amount = Column(Float, nullable=True)
    trigger_category = Column(String, nullable=True)

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Inicializa as tabelas do banco de dados"""
    Base.metadata.create_all(bind=engine)
    print("Banco de dados inicializado!")

def reset_db():
    """Remove e recria todas as tabelas - CUIDADO: apaga todos os dados!"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Banco de dados resetado!")

# Função auxiliar para criar usuário default se não existir
def create_default_user():
    """Cria usuário padrão para testes"""
    db = SessionLocal()
    try:
        # Verificar se usuário default já existe
        existing_user = db.query(User).filter(User.user_id == "default_user").first()
        if not existing_user:
            default_user = User(
                user_id="default_user",
                name="Usuário Teste",
                phone="+5511999999999"
            )
            db.add(default_user)
            db.commit()
            print("Usuário padrão criado!")
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar usuário padrão: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Executar para inicializar o banco
    print("Inicializando banco de dados...")
    init_db()
    create_default_user()
    print("Pronto!")
