import json
import pandas as pd
from registrador.Extrator import ExtratorFinanceiro
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import numpy as np

class ExtratorFinanceiroAvaliador:
    """Classe para avaliar o desempenho do extrator contra dados anotados"""

    def __init__(self, extrator: ExtratorFinanceiro):
        self.extrator = extrator

    def load_gold_data(self, filepath: str):
        """Carrega dados anotados do arquivo JSONL"""
        gold_data = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                gold_data.append(json.loads(line.strip()))
        return gold_data

    def avalia_extracao_valor(self, gold_data):
        """Avalia extração de valores monetários"""
        y_true = []
        y_pred = []
        errors = []

        for example in gold_data:
            text = example['raw_text']
            true_amount = example['amount']

            # Predição
            pred_amount, _ = self.extrator.extrai_valor(text)

            # Para avaliação binária: tem valor ou não tem
            y_true.append(true_amount is not None)
            y_pred.append(pred_amount is not None)

            # Verifica erro numérico (se ambos não são None)
            if true_amount is not None and pred_amount is not None:
                # Tolerância de ±0.01 para valores monetários
                if abs(true_amount - pred_amount) > 0.01:
                    errors.append({
                        'text': text,
                        'true_amount': true_amount,
                        'pred_amount': pred_amount,
                        'error': abs(true_amount - pred_amount)
                    })

        # Métricas
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary')

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'numerical_errors': errors
        }

    def avalia_extracao_categoria(self, gold_data):
        """Avalia extração de categorias"""
        y_true = []
        y_pred = []
        errors = []

        for example in gold_data:
            text = example['raw_text']
            true_category = example['category']

            pred_category, _ = self.extrator.extrai_categoria(text)

            y_true.append(true_category)
            y_pred.append(pred_category)

            if true_category != pred_category:
                errors.append({
                    'text': text,
                    'true_category': true_category,
                    'pred_category': pred_category
                })

        # Métricas
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted', zero_division=0
        )

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'errors': errors
        }

    def avalia_extracao_lugar(self, gold_data):
        """Avalia extração de locais"""
        y_true = []
        y_pred = []
        errors = []

        for example in gold_data:
            text = example['raw_text']
            true_place = example['place']

            pred_place, _ = self.extrator.extrai_lugar(text)

            # Para avaliação binária: tem lugar ou não tem
            y_true.append(true_place is not None)
            y_pred.append(pred_place is not None)

            if (true_place is None) != (pred_place is None) or (true_place != pred_place and true_place is not None):
                errors.append({
                    'text': text,
                    'true_place': true_place,
                    'pred_place': pred_place
                })

        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary')

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'errors': errors
        }

    def avalia_pipeline_completo(self, gold_data):
        """Avalia todo o pipeline de extração"""
        results = []

        for example in gold_data:
            text = example['raw_text']
            pred_result = self.extrator.aplica_extrator(text)

            # Compara cada campo
            result = {
                'text': text,
                'amount_correct': self._compare_amounts(example['amount'], pred_result['amount']),
                'category_correct': example['category'] == pred_result['category'],
                'place_correct': example['place'] == pred_result['place'],
                'type_correct': example['type'] == pred_result['type'],
                'confidence': pred_result['meta']['confidence']
            }
            results.append(result)

        return results

    def _compare_amounts(self, true_amount, pred_amount):
        """Compara valores monetários com tolerância"""
        if true_amount is None and pred_amount is None:
            return True
        if true_amount is None or pred_amount is None:
            return False
        return abs(true_amount - pred_amount) <= 0.01

    def generate_report(self, gold_data):
        """Gera relatório completo de avaliação"""

        print("="*50)
        print("RELATÓRIO DE AVALIAÇÃO DO EXTRATOR")
        print("="*50)

        # Avaliação por campo
        amount_metrics = self.avalia_extracao_valor(gold_data)
        category_metrics = self.avalia_extracao_categoria(gold_data)
        place_metrics = self.avalia_extracao_lugar(gold_data)

        print(f"\n📊 EXTRAÇÃO DE VALORES MONETÁRIOS:")
        print(f"   Precisão: {amount_metrics['precision']:.3f}")
        print(f"   Recall: {amount_metrics['recall']:.3f}")
        print(f"   F1-Score: {amount_metrics['f1_score']:.3f}")
        print(f"   Acurácia: {amount_metrics['accuracy']:.3f}")
        print(f"   Erros numéricos: {len(amount_metrics['numerical_errors'])}")

        print(f"\n🏷️  EXTRAÇÃO DE CATEGORIAS:")
        print(f"   Precisão: {category_metrics['precision']:.3f}")
        print(f"   Recall: {category_metrics['recall']:.3f}")
        print(f"   F1-Score: {category_metrics['f1_score']:.3f}")
        print(f"   Acurácia: {category_metrics['accuracy']:.3f}")
        print(f"   Erros de categoria: {len(category_metrics['errors'])}")

        print(f"\n📍 EXTRAÇÃO DE LOCAIS:")
        print(f"   Precisão: {place_metrics['precision']:.3f}")
        print(f"   Recall: {place_metrics['recall']:.3f}")
        print(f"   F1-Score: {place_metrics['f1_score']:.3f}")
        print(f"   Acurácia: {place_metrics['accuracy']:.3f}")
        print(f"   Erros de local: {len(place_metrics['errors'])}")

        # Avaliação completa
        full_results = self.avalia_pipeline_completo(gold_data)

        # Estatísticas gerais
        amount_accuracy = sum(1 for r in full_results if r['amount_correct']) / len(full_results)
        category_accuracy = sum(1 for r in full_results if r['category_correct']) / len(full_results)
        place_accuracy = sum(1 for r in full_results if r['place_correct']) / len(full_results)
        type_accuracy = sum(1 for r in full_results if r['type_correct']) / len(full_results)

        print(f"\n🎯 ACURÁCIA POR CAMPO:")
        print(f"   Valores: {amount_accuracy:.1%}")
        print(f"   Categorias: {category_accuracy:.1%}")
        print(f"   Locais: {place_accuracy:.1%}")
        print(f"   Tipos: {type_accuracy:.1%}")

        avg_confidence = np.mean([r['confidence'] for r in full_results])
        print(f"   Confiança média: {avg_confidence:.3f}")

        print(f"\n📈 RESUMO:")
        print(f"   Total de exemplos avaliados: {len(gold_data)}")

        # Critério de aceitação: ≥95% para amounts, ≥80% para categories
        amount_ok = amount_accuracy >= 0.95
        category_ok = category_accuracy >= 0.80

        print(f"   ✅ Valores ≥95%: {'SIM' if amount_ok else 'NÃO'}")
        print(f"   ✅ Categorias ≥80%: {'SIM' if category_ok else 'NÃO'}")

        if amount_ok and category_ok:
            print("\n🎉 CRITÉRIOS DE ACEITAÇÃO ATENDIDOS!")
        else:
            print("\n⚠️  CRITÉRIOS DE ACEITAÇÃO NÃO ATENDIDOS")

        # Salva resultados detalhados em CSV
        df_results = pd.DataFrame(full_results)
        df_results.to_csv('evaluation_results.csv', index=False, encoding='utf-8')
        print(f"\n💾 Resultados detalhados salvos em 'evaluation_results.csv'")

        return {
            'amount_metrics': amount_metrics,
            'category_metrics': category_metrics,
            'place_metrics': place_metrics,
            'summary': {
                'amount_accuracy': amount_accuracy,
                'category_accuracy': category_accuracy,
                'place_accuracy': place_accuracy,
                'type_accuracy': type_accuracy,
                'avg_confidence': avg_confidence,
                'meets_criteria': amount_ok and category_ok
            }
        }

def main():
    """Executa avaliação completa"""

    # Inicializa extrator e avaliador
    extrator = ExtratorFinanceiro()
    avaliador = ExtratorFinanceiroAvaliador(extrator)

    # Carrega dados de teste
    try:
        gold_data = avaliador.load_gold_data('data/sample_data.jsonl')
        print(f"Carregados {len(gold_data)} exemplos para avaliação")
    except FileNotFoundError:
        print("Erro: arquivo 'sample_data.jsonl' não encontrado!")
        return

    # Executa avaliação
    results = avaliador.generate_report(gold_data)

    return results

if __name__ == "__main__":
    main()
