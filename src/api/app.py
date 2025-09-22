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
from integrations.whatsapp_service import WhatsAppService, create_webhook_response, parse_whatsapp_webhook

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
whatsapp_service = WhatsAppService()

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
    Simula integração com WhatsApp ou outro sistema de mensagens
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
        
        return TransactionResponse(
            success=True,
            transaction_id=transaction_id,
            extracted_data=extracted_data,
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

# ==================== ENDPOINTS WHATSAPP ====================

@app.post("/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...),
    MessageSid: str = Form(...),
    AccountSid: str = Form(...)
):
    """
    Webhook para receber mensagens WhatsApp via Twilio
    Este endpoint será chamado pelo Twilio quando uma mensagem for recebida
    """
    try:
        # Parse dos dados do webhook
        form_data = await request.form()
        webhook_data = parse_whatsapp_webhook(dict(form_data))
        
        message_text = webhook_data['message']
        user_phone = webhook_data['from']
        
        logger.info(f"Mensagem WhatsApp recebida de {user_phone}: {message_text}")
        
        # Comandos especiais
        if message_text.lower() in ['saldo', 'balance', 'resumo']:
            dashboard_data = transaction_service.get_dashboard_data(user_phone)
            alerts = alert_service.get_active_alerts(user_phone)
            balance_message = create_balance_summary_message(dashboard_data, alerts)
            result = whatsapp_service.send_message(user_phone, balance_message)
            logger.info(f"Saldo enviado via API: {result.get('status', 'unknown')}")
            return Response(content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>", media_type="application/xml")
        
        if message_text.lower() in ['help', 'ajuda', 'comandos']:
            help_message = """GESTOR FINANCEIRO - COMANDOS

Para registrar transacoes:
- "Gastei R$ 25 no almoco"
- "Recebi R$ 1000 de salario"
- "Uber 15 reais para casa"
- "Netflix R$ 29,90 mensal"

Comandos uteis:
- saldo - Ver resumo financeiro
- ajuda - Mostrar estes comandos

Categorias reconhecidas:
Comida, Transporte, Saude, Lazer, Mercado, Moradia, Educacao

Alertas automaticos quando voce se aproxima dos seus limites!

Powered by Gestor Financeiro"""
            result = whatsapp_service.send_message(user_phone, help_message)
            logger.info(f"Ajuda enviada via API: {result.get('status', 'unknown')}")
            return Response(content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>", media_type="application/xml")
        
        # Processar transação normal
        extracted_data = extrator.aplica_extrator(message_text)
        
        # Se conseguiu extrair dados, processar transação
        if extracted_data.get('amount') is not None or extracted_data.get('type') != 'desconhecido':
            # Salvar transação no banco
            transaction_service.save_transaction(
                user_id=user_phone,
                raw_message=message_text,
                extracted_data=extracted_data,
                timestamp=datetime.now()
            )
            
            # Verificar alertas
            alerts = alert_service.check_alerts(user_phone, extracted_data)
            
            # Enviar resposta via API Twilio (contorna limitações do sandbox)
            response_message = create_transaction_confirmation_message(extracted_data, alerts)
            result = whatsapp_service.send_message(user_phone, response_message)
            logger.info(f"Resposta enviada via API: {result.get('status', 'unknown')}")
        else:
            error_message = """Nao consegui entender essa transacao.

Exemplos validos:
- "Gastei R$ 25 no almoco"
- "Recebi R$ 1000 de salario"
- "Uber 15 reais"
- "Netflix R$ 29,90"

Digite 'ajuda' para ver mais comandos."""
            result = whatsapp_service.send_message(user_phone, error_message)
            logger.info(f"Erro enviado via API: {result.get('status', 'unknown')}")
        
        # Retornar TwiML vazio (já enviamos via API)
        logger.info(f"Resposta enviada via API Twilio para {user_phone}")
        return Response(content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>", media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Erro no webhook WhatsApp: {str(e)}")
        try:
            error_message = "Ops! Houve um erro ao processar sua mensagem. Tente novamente."
            # Tentar enviar erro via API se possível
            webhook_data = parse_whatsapp_webhook(dict(await request.form()))
            user_phone = webhook_data.get('from', '')
            if user_phone:
                whatsapp_service.send_message(user_phone, error_message)
        except:
            pass  # Se falhar, não faz nada
        
        return Response(content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>", media_type="application/xml")

def handle_balance_request(user_phone: str):
    """Processa solicitação de saldo"""
    try:
        dashboard_data = transaction_service.get_dashboard_data(user_phone)
        alerts = alert_service.get_active_alerts(user_phone)
        
        # Criar resposta de saldo formatada
        balance_message = create_balance_summary_message(dashboard_data, alerts)
        
        twiml_response = create_webhook_response(balance_message)
        logger.info(f"Enviando resposta saldo TwiML: {twiml_response}")
        headers = {"Content-Type": "application/xml; charset=utf-8", "Cache-Control": "no-cache"}
        return Response(content=twiml_response, media_type="application/xml", headers=headers)
        
    except Exception as e:
        logger.error(f"Erro ao buscar saldo: {str(e)}")
        twiml_response = create_webhook_response("Erro ao buscar saldo. Tente novamente.")
        headers = {"Content-Type": "application/xml; charset=utf-8", "Cache-Control": "no-cache"}
        return Response(content=twiml_response, media_type="application/xml", headers=headers)

def handle_help_request(user_phone: str = None):
    """Processa solicitação de ajuda"""
    help_message = """GESTOR FINANCEIRO - COMANDOS

Para registrar transacoes:
- "Gastei R$ 25 no almoco"
- "Recebi R$ 1000 de salario"
- "Uber 15 reais para casa"
- "Netflix R$ 29,90 mensal"

Comandos uteis:
- saldo - Ver resumo financeiro
- ajuda - Mostrar estes comandos

Categorias reconhecidas:
Comida, Transporte, Saude, Lazer, Mercado, Moradia, Educacao

Alertas automaticos quando voce se aproxima dos seus limites!

Powered by Gestor Financeiro"""
    
    twiml_response = create_webhook_response(help_message)
    headers = {"Content-Type": "application/xml; charset=utf-8", "Cache-Control": "no-cache"}
    return Response(content=twiml_response, media_type="application/xml", headers=headers)

@app.post("/whatsapp/send")
async def send_whatsapp_message(to_number: str, message: str):
    """Endpoint para enviar mensagem WhatsApp manualmente (para testes)"""
    try:
        result = whatsapp_service.send_message(to_number, message)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar: {str(e)}")

def create_transaction_confirmation_message(transaction_data: Dict[str, Any], alerts: List[str] = None) -> str:
    """Cria mensagem de confirmação formatada para webhook"""
    tipo = transaction_data.get('type', 'transação')
    valor = transaction_data.get('amount', 0)
    categoria = transaction_data.get('category', 'N/A')
    
    if tipo == 'gasto':
        action = 'GASTO REGISTRADO'
    elif tipo == 'receita':
        action = 'RECEITA REGISTRADA'
    else:
        action = 'TRANSACAO REGISTRADA'
    
    message = f"""{action}

Valor: R$ {valor:.2f}
Categoria: {categoria}
Data: {transaction_data.get('date', 'hoje')}

Transacao salva com sucesso!"""

    # Adicionar alertas se houver
    if alerts:
        message += "\n\nALERTAS:"
        for alert in alerts[:2]:  # Máximo 2 alertas para não ficar muito longo
            # Limpar emojis dos alertas
            clean_alert = alert.replace("⚠️", "AVISO:").replace("🚨", "CRITICO:")
            message += f"\n{clean_alert}"
    
    message += "\n\nDigite 'saldo' para ver seu resumo"
    
    return message

def create_balance_summary_message(dashboard_data: Dict[str, Any], alerts: List[str] = None) -> str:
    """Cria mensagem de resumo de saldo formatada"""
    total_balance = dashboard_data.get('total_balance', 0)
    monthly_expenses = dashboard_data.get('monthly_expenses', {})
    
    # Calcular total de gastos
    total_expenses = sum(monthly_expenses.values())
    
    message = f"""SEU RESUMO FINANCEIRO

Saldo Atual: R$ {total_balance:.2f}
Gastos do Mes: R$ {total_expenses:.2f}

Por Categoria:"""
    
    # Adicionar categorias (máximo 4 para não ficar muito longo)
    for categoria, valor in list(monthly_expenses.items())[:4]:
        message += f"\n- {categoria}: R$ {valor:.2f}"
    
    if len(monthly_expenses) > 4:
        message += f"\n- ... e mais {len(monthly_expenses) - 4} categorias"
    
    # Adicionar alertas se houver
    if alerts:
        message += "\n\nALERTAS ATIVOS:"
        for alert in alerts[:2]:  # Máximo 2 alertas
            # Limpar emojis dos alertas para evitar duplicação
            clean_alert = alert.replace("⚠️", "AVISO:").replace("🚨", "CRITICO:").strip()
            message += f"\n- {clean_alert}"
    
    message += "\n\nDigite uma transacao para registrar"
    
    return message

# Função auxiliar para processar alertas em background
def check_and_send_alerts(user_id: str, transaction_data: Dict[str, Any]):
    """Verifica e envia alertas em background"""
    try:
        alerts = alert_service.process_transaction_alerts(user_id, transaction_data)
        if alerts:
            logger.info(f"Alertas gerados para usuário {user_id}: {alerts}")
            # Aqui seria onde enviariamos alertas via WhatsApp/chat
            # Por enquanto só logar
    except Exception as e:
        logger.error(f"Erro ao processar alertas: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
