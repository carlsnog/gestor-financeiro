"""
Backend do Gestor Financeiro via Chat
API principal usando FastAPI para receber mensagens e processar transações
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import uvicorn

# Imports internos
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services.transaction_service import TransactionService
from core.services.alert_service import AlertService
from core.models.database import init_db
from core.registrador.Extrator import ExtratorFinanceiro

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gestor Financeiro API",
    description="API para processamento de mensagens financeiras via chat",
    version="1.0.0"
)

# Inicializar serviços
extrator = ExtratorFinanceiro()
transaction_service = TransactionService()
alert_service = AlertService()

# Modelos Pydantic
class MessageRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    timestamp: Optional[datetime] = None

class TransactionResponse(BaseModel):
    success: bool
    transaction_id: Optional[int] = None
    extracted_data: Optional[Dict[str, Any]] = None
    alerts: Optional[List[str]] = None
    message: str

class DashboardData(BaseModel):
    total_balance: float
    monthly_expenses: Dict[str, float]
    recent_transactions: List[Dict[str, Any]]
    alerts: List[str]

@app.on_event("startup")
async def startup_event():
    """Inicializa o banco de dados na inicialização"""
    logger.info("Inicializando banco de dados...")
    init_db()
    logger.info("Backend iniciado com sucesso!")

@app.get("/")
async def root():
    """Endpoint de health check"""
    return {"message": "Gestor Financeiro API está funcionando!", "status": "online"}

@app.post("/webhook/message", response_model=TransactionResponse)
async def process_message(request: MessageRequest, background_tasks: BackgroundTasks):
    """
    Endpoint principal para receber mensagens de chat e processar transações
    Simula integração com sistema de mensagens
    """
    try:
        logger.info(f"Processando mensagem: {request.message}")
        
        # 1. Extrair dados da mensagem usando o ExtratorFinanceiro
        extracted_data = extrator.aplica_extrator(request.message)
        logger.info(f"Dados extraídos: {extracted_data}")
        
        # 2. Se conseguiu extrair alguma informação válida, salvar no banco
        transaction_id = None
        if extracted_data.get('amount') is not None or extracted_data.get('type') != 'desconhecido':
            transaction_id = transaction_service.save_transaction(
                user_id=request.user_id,
                raw_message=request.message,
                extracted_data=extracted_data,
                timestamp=request.timestamp or datetime.now()
            )
            logger.info(f"Transação salva com ID: {transaction_id}")
        
        # 3. Verificar alertas em background
        alerts = []
        if transaction_id:
            background_tasks.add_task(
                check_and_send_alerts,
                request.user_id,
                extracted_data
            )
            
            # Verificar alertas imediatos
            alerts = alert_service.check_alerts(request.user_id, extracted_data)
        
        # Criar resposta com dados extraídos formatados
        response_data = {
            "raw_text": extracted_data.get("raw_text"),
            "type": extracted_data.get("type"),
            "amount": extracted_data.get("amount"),
            "currency": extracted_data.get("currency"),
            "category": extracted_data.get("category"),
            "details": extracted_data.get("details"),
            "confidence": extracted_data.get("meta", {}).get("confidence"),
            "extraction_metadata": extracted_data.get("meta", {})
        }
        
        return TransactionResponse(
            success=True,
            transaction_id=transaction_id,
            extracted_data=response_data,
            alerts=alerts,
            message="Mensagem processada com sucesso!"
        )
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/dashboard/{user_id}", response_model=DashboardData)
async def get_dashboard_data(user_id: str):
    """Retorna dados do dashboard para um usuário"""
    try:
        dashboard_data = transaction_service.get_dashboard_data(user_id)
        alerts = alert_service.get_active_alerts(user_id)
        
        return DashboardData(
            total_balance=dashboard_data['total_balance'],
            monthly_expenses=dashboard_data['monthly_expenses'],
            recent_transactions=dashboard_data['recent_transactions'],
            alerts=alerts
        )
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados do dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/transactions/{user_id}")
async def get_transactions(user_id: str, limit: int = 50):
    """Retorna lista de transações do usuário"""
    try:
        transactions = transaction_service.get_user_transactions(user_id, limit)
        return {"transactions": transactions}
    except Exception as e:
        logger.error(f"Erro ao buscar transações: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/alerts/configure")
async def configure_alerts(user_id: str, alert_config: Dict[str, Any]):
    """Configura alertas personalizados para um usuário"""
    try:
        alert_service.configure_user_alerts(user_id, alert_config)
        return {"message": "Alertas configurados com sucesso!"}
    except Exception as e:
        logger.error(f"Erro ao configurar alertas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/stats/{user_id}")
async def get_user_stats(user_id: str, period: str = "month"):
    """Retorna estatísticas do usuário por período"""
    try:
        stats = transaction_service.get_user_stats(user_id, period)
        return stats
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")



# Função auxiliar para processar alertas em background
def check_and_send_alerts(user_id: str, transaction_data: Dict[str, Any]):
    """Verifica e envia alertas em background"""
    try:
        alerts = alert_service.process_transaction_alerts(user_id, transaction_data)
        if alerts:
            logger.info(f"Alertas gerados para usuário {user_id}: {alerts}")
            # Aqui seria onde enviariamos alertas via chat
            # Por enquanto só logar
    except Exception as e:
        logger.error(f"Erro ao processar alertas: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
