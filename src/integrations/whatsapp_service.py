"""
Integração WhatsApp usando Twilio
Permite receber e enviar mensagens via WhatsApp
"""

import os
from typing import Dict, Any, Optional
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import logging
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

logger = logging.getLogger(__name__)

class WhatsAppService:
    """Serviço para integração WhatsApp via Twilio"""
    
    def __init__(self):
        # Credenciais Twilio (carregar diretamente do .env)
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')  # Sandbox
        
        logger.info(f"Inicializando WhatsApp Service...")
        logger.info(f"Account SID: {'✅ Configurado' if self.account_sid else '❌ Não encontrado'}")
        logger.info(f"Auth Token: {'✅ Configurado' if self.auth_token else '❌ Não encontrado'}")
        logger.info(f"WhatsApp Number: {self.whatsapp_number}")
        
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                # Testar conexão
                account = self.client.api.accounts(self.account_sid).fetch()
                logger.info(f"✅ Twilio WhatsApp client inicializado com sucesso! Status: {account.status}")
            except Exception as e:
                logger.error(f"❌ Erro ao conectar com Twilio: {str(e)}")
                self.client = None
        else:
            self.client = None
            logger.warning("❌ Credenciais Twilio não configuradas - modo desenvolvimento")
    
    def send_message(self, to_number: str, message: str) -> Dict[str, Any]:
        """Envia mensagem WhatsApp via Twilio"""
        if not self.client:
            logger.error(f"❌ Cliente Twilio não configurado - NÃO ENVIANDO mensagem para {to_number}")
            logger.error("Verifique suas credenciais TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN no .env")
            return {
                "status": "error",
                "message": "Cliente Twilio não configurado",
                "to": to_number,
                "body": message
            }
        
        try:
            # Normalizar e garantir formato correto do número
            clean_number = to_number.replace('whatsapp:', '').strip()
            if clean_number and not clean_number.startswith('+'):
                clean_number = f'+{clean_number}'
            to_number = f'whatsapp:{clean_number}'
            
            message_obj = self.client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=to_number
            )
            
            logger.info(f"Mensagem enviada com sucesso: {message_obj.sid}")
            return {
                "status": "sent",
                "sid": message_obj.sid,
                "to": to_number,
                "body": message
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem WhatsApp: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "to": to_number,
                "body": message
            }
    
    def send_transaction_alert(self, user_phone: str, alert_message: str) -> Dict[str, Any]:
        """Envia alerta de transação via WhatsApp"""
        formatted_message = f"🚨 *ALERTA FINANCEIRO*\n\n{alert_message}\n\n_Gestor Financeiro_"
        return self.send_message(user_phone, formatted_message)
    
    def send_transaction_confirmation(self, user_phone: str, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Envia confirmação de transação processada"""
        tipo = transaction_data.get('type', 'transação')
        valor = transaction_data.get('amount', 0)
        categoria = transaction_data.get('category', 'N/A')
        
        if tipo == 'gasto':
            emoji = '💸'
            action = 'Gasto registrado'
        elif tipo == 'receita':
            emoji = '💰'
            action = 'Receita registrada'
        else:
            emoji = '💱'
            action = 'Transação registrada'
        
        message = f"""
{emoji} *{action}*

💵 *Valor:* R$ {valor:.2f}
📂 *Categoria:* {categoria}
📅 *Data:* {transaction_data.get('date', 'hoje')}

✅ Transação salva com sucesso!

_Digite "saldo" para ver seu saldo atual_
        """.strip()
        
        return self.send_message(user_phone, message)
    
    def send_balance_summary(self, user_phone: str, balance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Envia resumo de saldo"""
        total_balance = balance_data.get('total_balance', 0)
        monthly_expenses = balance_data.get('monthly_expenses', {})
        
        # Calcular total de gastos
        total_expenses = sum(monthly_expenses.values())
        
        message = f"""
💰 *SEU RESUMO FINANCEIRO*

🏦 *Saldo Atual:* R$ {total_balance:.2f}
💸 *Gastos do Mês:* R$ {total_expenses:.2f}

📊 *Por Categoria:*
        """
        
        for categoria, valor in monthly_expenses.items():
            message += f"\n• {categoria}: R$ {valor:.2f}"
        
        if balance_data.get('alerts'):
            message += "\n\n🚨 *ALERTAS ATIVOS:*"
            for alert in balance_data['alerts'][:3]:  # Máximo 3 alertas
                message += f"\n⚠️ {alert}"
        
        message += "\n\n_Digite uma transação para registrar_"
        
        return self.send_message(user_phone, message)

def create_webhook_response(message: str) -> str:
    """Cria resposta TwiML para webhook"""
    response = MessagingResponse()
    response.message(message)
    return str(response)

def parse_whatsapp_webhook(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse dos dados do webhook Twilio"""
    # Normalizar número de telefone
    from_number = request_data.get('From', '').replace('whatsapp:', '').strip()
    if from_number and not from_number.startswith('+'):
        from_number = f'+{from_number}'
    
    return {
        "message": request_data.get('Body', ''),
        "from": from_number,
        "to": request_data.get('To', ''),
        "message_sid": request_data.get('MessageSid', ''),
        "account_sid": request_data.get('AccountSid', '')
    }
