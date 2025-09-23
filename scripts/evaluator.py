"""
Script de avaliação do sistema de extração financeira
Calcula métricas de precision, recall e accuracy
"""

import json
import requests
import sys
import os
from typing import Dict, List, Any
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

# Adicionar path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from core.registrador.Extrator import ExtratorFinanceiro

@dataclass
class EvaluationMetrics:
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    total_samples: int
    correct_extractions: int

class FinancialExtractorEvaluator:
    """Avaliador do sistema de extração financeira"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.extrator = ExtratorFinanceiro()
        
    def load_test_data(self, file_path: str) -> List[Dict]:
        """Carrega dados de teste do arquivo JSONL"""
        test_data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    test_data.append(json.loads(line.strip()))
        except FileNotFoundError:
            print(f"Arquivo {file_path} não encontrado")
        return test_data
    
    def create_ground_truth_samples(self) -> List[Dict]:
        """Cria amostras com ground truth para avaliação"""
        return [
            {
                "text": "Gastei R$ 25,50 no almoço",
                "expected": {
                    "type": "gasto",
                    "amount": 25.50,
                    "category": "Comida"
                }
            },
            {
                "text": "Recebi meu salário de R$ 3500",
                "expected": {
                    "type": "receita", 
                    "amount": 3500.0,
                    "category": "Salário"
                }
            },
            {
                "text": "Uber para casa 15 reais",
                "expected": {
                    "type": "gasto",
                    "amount": 15.0,
                    "category": "Transporte"
                }
            },
            {
                "text": "Compras no mercado R$ 120,80",
                "expected": {
                    "type": "gasto",
                    "amount": 120.80,
                    "category": "Mercado"
                }
            },
            {
                "text": "Netflix 29,90 mensal",
                "expected": {
                    "type": "gasto",
                    "amount": 29.90,
                    "category": "Lazer"
                }
            },
            {
                "text": "Transferi R$ 500 para João",
                "expected": {
                    "type": "transferencia",
                    "amount": 500.0,
                    "category": "Outros"
                }
            },
            {
                "text": "Consulta médica R$ 150",
                "expected": {
                    "type": "gasto",
                    "amount": 150.0,
                    "category": "Saúde"
                }
            },
            {
                "text": "Aluguel 1.500,00 reais",
                "expected": {
                    "type": "gasto",
                    "amount": 1500.0,
                    "category": "Moradia"
                }
            },
            {
                "text": "Livros da faculdade R$ 80",
                "expected": {
                    "type": "gasto", 
                    "amount": 80.0,
                    "category": "Educação"
                }
            },
            {
                "text": "Cinema R$ 22 no shopping",
                "expected": {
                    "type": "gasto",
                    "amount": 22.0,
                    "category": "Lazer"
                }
            }
        ]
    
    def evaluate_extraction(self, text: str, expected: Dict) -> Dict[str, bool]:
        """Avalia uma extração específica"""
        extracted = self.extrator.aplica_extrator(text)
        
        results = {}
        
        # Avaliar tipo de transação
        results['type_correct'] = extracted.get('type') == expected.get('type')
        
        # Avaliar valor (com tolerância de 0.01)
        expected_amount = expected.get('amount')
        extracted_amount = extracted.get('amount')
        if expected_amount is not None and extracted_amount is not None:
            results['amount_correct'] = abs(extracted_amount - expected_amount) < 0.01
        else:
            results['amount_correct'] = expected_amount == extracted_amount
        
        # Avaliar categoria
        results['category_correct'] = extracted.get('category') == expected.get('category')
        
        # Avaliar extração geral (todos os campos corretos)
        results['overall_correct'] = all([
            results['type_correct'],
            results['amount_correct'], 
            results['category_correct']
        ])
        
        return {
            'results': results,
            'extracted': extracted,
            'expected': expected
        }
    
    def run_full_evaluation(self) -> EvaluationMetrics:
        """Executa avaliação completa do sistema"""
        test_samples = self.create_ground_truth_samples()
        
        all_results = []
        correct_count = 0
        
        print("🧪 Executando avaliação do extrator...")
        print("-" * 50)
        
        for i, sample in enumerate(test_samples, 1):
            text = sample['text']
            expected = sample['expected']
            
            evaluation = self.evaluate_extraction(text, expected)
            all_results.append(evaluation)
            
            if evaluation['results']['overall_correct']:
                correct_count += 1
                status = "✅"
            else:
                status = "❌"
            
            print(f"{status} [{i:2d}] {text}")
            
            # Mostrar detalhes dos erros
            if not evaluation['results']['overall_correct']:
                extracted = evaluation['extracted']
                if not evaluation['results']['type_correct']:
                    print(f"    🔴 Tipo: esperado '{expected.get('type')}', obtido '{extracted.get('type')}'")
                if not evaluation['results']['amount_correct']:
                    print(f"    🔴 Valor: esperado {expected.get('amount')}, obtido {extracted.get('amount')}")
                if not evaluation['results']['category_correct']:
                    print(f"    🔴 Categoria: esperado '{expected.get('category')}', obtido '{extracted.get('category')}'")
        
        print("-" * 50)
        
        # Calcular métricas
        accuracy = correct_count / len(test_samples) if test_samples else 0
        
        # Para precision/recall, consideramos cada campo como um item
        tp_type = sum(1 for r in all_results if r['results']['type_correct'])
        tp_amount = sum(1 for r in all_results if r['results']['amount_correct'])
        tp_category = sum(1 for r in all_results if r['results']['category_correct'])
        
        total_fields = len(test_samples) * 3  # 3 campos por amostra
        tp_total = tp_type + tp_amount + tp_category
        
        precision = tp_total / total_fields if total_fields > 0 else 0
        recall = precision  # Para este caso, precision == recall
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return EvaluationMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            accuracy=accuracy,
            total_samples=len(test_samples),
            correct_extractions=correct_count
        )
    
    def test_api_integration(self) -> Dict[str, Any]:
        """Testa integração com a API"""
        print("🔗 Testando integração com API...")
        
        # Verificar se API está rodando
        try:
            response = requests.get(f"{self.api_url}/", timeout=5)
            api_status = "online" if response.status_code == 200 else "error"
        except:
            api_status = "offline"
        
        if api_status != "online":
            return {
                "status": api_status, 
                "processing_status": "offline",
                "message": "API não está acessível"
            }
        
        # Testar processamento de mensagem
        test_message = "Gastei R$ 50 no almoço hoje"
        try:
            response = requests.post(f"{self.api_url}/webhook/message", json={
                "message": test_message,
                "user_id": "test_evaluation"
            }, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                processing_status = "success" if result.get("success") else "error"
            else:
                processing_status = "http_error"
                result = {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            processing_status = "exception"
            result = {"error": str(e)}
        
        return {
            "status": api_status,
            "processing_status": processing_status,
            "test_result": result,
            "message": "Integração testada com sucesso" if processing_status == "success" else "Erro na integração"
        }
    
    def generate_report(self, metrics: EvaluationMetrics, api_test: Dict) -> str:
        """Gera relatório de avaliação"""
        report = f"""
📊 RELATÓRIO DE AVALIAÇÃO - GESTOR FINANCEIRO
{'=' * 60}

🕒 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

📈 MÉTRICAS DE EXTRAÇÃO:
  • Precisão (Precision): {metrics.precision:.3f} ({metrics.precision*100:.1f}%)
  • Revocação (Recall):   {metrics.recall:.3f} ({metrics.recall*100:.1f}%)
  • F1-Score:             {metrics.f1_score:.3f} ({metrics.f1_score*100:.1f}%)
  • Acurácia:             {metrics.accuracy:.3f} ({metrics.accuracy*100:.1f}%)
  
  • Total de amostras:    {metrics.total_samples}
  • Extrações corretas:   {metrics.correct_extractions}
  • Taxa de erro:         {(1-metrics.accuracy)*100:.1f}%

🔗 TESTE DE INTEGRAÇÃO:
  • Status da API:        {api_test['status'].upper()}
  • Processamento:        {api_test['processing_status'].upper()}
  • Resultado:            {api_test['message']}

"""
        return report

def main():
    """Executa avaliação completa"""
    evaluator = FinancialExtractorEvaluator()
    
    print("🚀 INICIANDO AVALIAÇÃO DO GESTOR FINANCEIRO")
    print("=" * 60)
    
    # Avaliar extração
    metrics = evaluator.run_full_evaluation()
    
    # Testar API
    api_test = evaluator.test_api_integration()
    
    # Gerar relatório
    report = evaluator.generate_report(metrics, api_test)
    print(report)
    
    # Salvar relatório
    with open("evaluation_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    

if __name__ == "__main__":
    main()
