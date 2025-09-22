#!/usr/bin/env python3
"""
Script para testar integração WhatsApp
Simula envio de mensagens para o webhook
"""

import os
import sys
import requests
from datetime import datetime

# Adicionar path do src
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_webhook_endpoint():
    """Testa o endpoint webhook do WhatsApp"""
    
    webhook_url = "http://localhost:8000/whatsapp/webhook"
    test_phone = "+5511999999999"
    
    print("🧪 Testando Webhook WhatsApp...")
    print(f"URL: {webhook_url}")
    print("-" * 50)
    
    # Simular dados de webhook do Twilio
    test_messages = [
        "Gastei R$ 45 no almoço hoje",
        "saldo",
        "Recebi R$ 2500 de freelance", 
        "ajuda",
        "Netflix R$ 29,90 mensal",
        "Uber 25 reais para casa"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"[{i}] Testando: '{message}'")
        
        # Dados no formato que o Twilio envia
        form_data = {
            'Body': message,
            'From': f'whatsapp:{test_phone}',
            'To': 'whatsapp:+14155238886',
            'MessageSid': f'SM{datetime.now().strftime("%Y%m%d%H%M%S")}{i:03d}',
            'AccountSid': 'ACtest123'
        }
        
        try:
            response = requests.post(webhook_url, data=form_data, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Sucesso! Resposta: {response.text[:100]}...")
            else:
                print(f"❌ Erro HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Erro: API não está rodando! Execute ./run_backend.sh primeiro")
            return False
        except Exception as e:
            print(f"❌ Erro: {str(e)}")
        
        print()
    
    return True

def test_send_message():
    """Testa envio direto de mensagem"""
    
    send_url = "http://localhost:8000/whatsapp/send"
    test_phone = "+5511999999999"
    test_message = "🤖 Mensagem de teste do Gestor Financeiro!"
    
    print("📤 Testando Envio Direto...")
    print(f"URL: {send_url}")
    print(f"Para: {test_phone}")
    print("-" * 50)
    
    try:
        response = requests.post(send_url, json={
            "to_number": test_phone,
            "message": test_message
        }, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Sucesso!")
            print(f"Status: {result.get('result', {}).get('status', 'unknown')}")
            
            if result.get('result', {}).get('status') == 'simulated':
                print("ℹ️ Modo simulação (Twilio não configurado)")
            else:
                print("🚀 Mensagem enviada via Twilio!")
                
        else:
            print(f"❌ Erro HTTP {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro: API não está rodando! Execute ./run_backend.sh primeiro")
        return False
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False
    
    return True

def check_api_health():
    """Verifica se a API está rodando"""
    
    health_url = "http://localhost:8000/"
    
    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Online: {data.get('message', 'OK')}")
            return True
        else:
            print(f"❌ API com problemas: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ API offline! Execute ./run_backend.sh primeiro")
        return False
    except Exception as e:
        print(f"❌ Erro ao verificar API: {str(e)}")
        return False

def show_setup_status():
    """Mostra status da configuração"""
    
    print("⚙️ Status da Configuração:")
    print("-" * 30)
    
    # Verificar arquivo .env
    if os.path.exists('.env'):
        print("✅ Arquivo .env encontrado")
        
        # Ler variáveis
        twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
        twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        if twilio_sid and twilio_sid != 'your_account_sid_here':
            print("✅ TWILIO_ACCOUNT_SID configurado")
        else:
            print("⚠️ TWILIO_ACCOUNT_SID não configurado")
            
        if twilio_token and twilio_token != 'your_auth_token_here':
            print("✅ TWILIO_AUTH_TOKEN configurado")
        else:
            print("⚠️ TWILIO_AUTH_TOKEN não configurado")
    else:
        print("❌ Arquivo .env não encontrado")
        print("💡 Execute ./setup.sh para criar")
    
    print()

def main():
    """Função principal"""
    
    print("📱 TESTE DE INTEGRAÇÃO WHATSAPP")
    print("=" * 50)
    print()
    
    # Status da configuração
    show_setup_status()
    
    # Verificar API
    if not check_api_health():
        print("\n💡 Para iniciar a API execute: ./run_backend.sh")
        return
    
    print()
    
    # Testes
    test_webhook_endpoint()
    print()
    test_send_message()
    
    print("\n" + "=" * 50)
    print("🎯 PRÓXIMOS PASSOS:")
    print("1. Configure credenciais Twilio no arquivo .env")
    print("2. Leia o guia completo em: WHATSAPP_SETUP.md")
    print("3. Configure ngrok para webhook público") 
    print("4. Teste com WhatsApp real!")
    print()
    print("📚 Documentação: http://localhost:8000/docs")
    
if __name__ == "__main__":
    main()
