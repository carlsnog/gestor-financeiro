"""
Simulador de mensagens para testar a API
"""

import requests
import json
import time
import sys
import os
from typing import List, Dict
from datetime import datetime

# Adicionar path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

class MessageSimulator:
    """Simula envio de mensagens para a API"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.user_id = "test_user"
    
    def send_message(self, message: str) -> Dict:
        """Envia uma mensagem para a API"""
        endpoint = f"{self.api_url}/webhook/message"
        
        payload = {
            "message": message,
            "user_id": self.user_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            response = requests.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def send_batch_messages(self, messages: List[str], delay: float = 0.5):
        """Envia várias mensagens com intervalo"""
        results = []
        
        print(f"Enviando {len(messages)} mensagens...")
        for i, message in enumerate(messages, 1):
            print(f"[{i}/{len(messages)}] Enviando: {message}")
            
            result = self.send_message(message)
            results.append({
                "message": message,
                "response": result,
                "timestamp": datetime.now().isoformat()
            })
            
            if result.get("success"):
                print(f"✅ Processada com sucesso!")
                if result.get("alerts"):
                    for alert in result["alerts"]:
                        print(f"🚨 ALERTA: {alert}")
            else:
                print(f"❌ Erro: {result}")
            
            time.sleep(delay)
        
        return results
    
    def get_dashboard(self) -> Dict:
        """Busca dados do dashboard"""
        endpoint = f"{self.api_url}/dashboard/{self.user_id}"
        
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_transactions(self) -> Dict:
        """Busca transações do usuário"""
        endpoint = f"{self.api_url}/transactions/{self.user_id}"
        
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

def run_demo():
    """Executa demonstração do sistema"""
    simulator = MessageSimulator()
    
    # Mensagens de teste
    test_messages = [
        "Gastei R$ 45 no almoço hoje",
        "Paguei R$ 15 no uber para casa",
        "Comprei um café por 8 reais",
        "Recebi meu salário de R$ 3500 hoje",
        "R$ 120 no supermercado Extra",
        "Pagamento de R$ 1500 do aluguel",
        "Netflix R$ 29,90 mensal",
        "Gastei 80 reais na farmácia",
        "Jantar romântico custou R$ 95,50",
        "Transferi R$ 200 para minha mãe",
        "Posto de gasolina R$ 180",
        "Academia mensal 79,90",
        "Pizza delivery 42,90",
        "Cortei o cabelo por 35 reais",
        "Comprei livros por R$ 60"
    ]
    
    print("=== SIMULADOR DE MENSAGENS FINANCEIRAS ===")
    print()
    
    # Testar conexão
    try:
        health = requests.get(f"{simulator.api_url}/")
        print(f"✅ API conectada: {health.json()}")
        print()
    except:
        print("❌ Erro: API não está rodando. Execute primeiro: uvicorn app:app")
        return
    
    # Enviar mensagens
    results = simulator.send_batch_messages(test_messages)
    
    print("\n=== RESUMO DOS RESULTADOS ===")
    successful = sum(1 for r in results if r["response"].get("success"))
    print(f"Mensagens processadas com sucesso: {successful}/{len(results)}")
    
    # Mostrar dashboard
    print("\n=== DASHBOARD ===")
    dashboard = simulator.get_dashboard()
    if "error" not in dashboard:
        print(f"Saldo atual: R$ {dashboard['total_balance']:.2f}")
        print(f"Gastos por categoria:")
        for category, amount in dashboard['monthly_expenses'].items():
            print(f"  - {category}: R$ {amount:.2f}")
        
        if dashboard['alerts']:
            print("Alertas ativos:")
            for alert in dashboard['alerts']:
                print(f"  - {alert}")
    else:
        print(f"Erro ao buscar dashboard: {dashboard['error']}")

if __name__ == "__main__":
    run_demo()
