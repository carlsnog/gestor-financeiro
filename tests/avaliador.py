import json
import pandas as pd
from registrador.Extrator import ExtratorFinanceiro
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import numpy as np
import joblib
from pathlib import Path

class ExtratorFinanceiroAvaliador:
    """Classe para avaliar o desempenho do extrator contra dados anotados,
    agora com seções adicionais: avaliação do modelo puro e avaliação do pipeline híbrido.
    """

    def __init__(self, extrator: ExtratorFinanceiro, model_artifact_path: str = "modelos/category_model_tfidf_lr.joblib"):
        self.extrator = extrator
        self.model_artifact_path = Path(model_artifact_path)
        self.model_estimator = None
        self.model_loaded = False
        self._try_load_model()

    def _try_load_model(self):
        """Tenta carregar artefato de modelo (joblib). Suporta artefato dict{'model': estimator} ou estimator direto."""
        if not self.model_artifact_path.exists():
            print(f"[Avaliador] Artefato de modelo não encontrado em {self.model_artifact_path}. Seções relativas ao modelo serão ignoradas.")
            self.model_loaded = False
            return

        try:
            artifact = joblib.load(self.model_artifact_path)
            if isinstance(artifact, dict) and "model" in artifact:
                self.model_estimator = artifact["model"]
            else:
                self.model_estimator = artifact
            self.model_loaded = True
            print(f"[Avaliador] Modelo carregado de {self.model_artifact_path}.")
        except Exception as e:
            print(f"[Avaliador] Falha ao carregar modelo: {e}")
            self.model_loaded = False

    def load_gold_data(self, filepath: str):
        """Carrega dados anotados do arquivo JSONL"""
        gold_data = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                gold_data.append(json.loads(line))
        return gold_data

    # -----------------------
    # Avaliação de valores
    # -----------------------
    def avalia_extracao_valor(self, gold_data):
        """Avalia extração de valores monetários (mesma lógica que você tinha)"""
        y_true = []
        y_pred = []
        errors = []

        for example in gold_data:
            text = example['raw_text']
            true_amount = example.get('amount', None)

            # Predição
            pred_amount, _ = self.extrator.extrai_valor(text)

            # Para avaliação binária: tem valor ou não tem
            y_true.append(true_amount is not None)
            y_pred.append(pred_amount is not None)

            # Verifica erro numérico (se ambos não são None)
            if true_amount is not None and pred_amount is not None:
                if abs(true_amount - pred_amount) > 0.01:
                    errors.append({
                        'text': text,
                        'true_amount': true_amount,
                        'pred_amount': pred_amount,
                        'error': abs(true_amount - pred_amount)
                    })

        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', zero_division=0)

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'numerical_errors': errors
        }

    # -----------------------
    # Avaliação de categoria (rule-based)
    # -----------------------
    def avalia_extracao_categoria(self, gold_data):
        """Avalia extração de categorias por keyword (rule-based)"""
        y_true = []
        y_pred = []
        errors = []

        for example in gold_data:
            text = example['raw_text']
            true_category = example.get('category', None)

            pred_category, _ = self.extrator.extrai_categoria_keyword(text)

            y_true.append(true_category)
            y_pred.append(pred_category)

            if true_category != pred_category:
                errors.append({
                    'text': text,
                    'true_category': true_category,
                    'pred_category': pred_category
                })

        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted', zero_division=0
        )

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'errors': errors,
            'y_true': y_true,
            'y_pred': y_pred
        }

    # -----------------------
    # Avaliação do pipeline completo (híbrido) — já tinha
    # -----------------------
    def avalia_pipeline_completo(self, gold_data):
        """Avalia todo o pipeline de extração (usa aplica_extrator)"""
        results = []

        for example in gold_data:
            text = example['raw_text']
            pred_result = self.extrator.aplica_extrator(text)

            result = {
                'text': text,
                'amount_correct': self._compare_amounts(example.get('amount', None), pred_result.get('amount', None)),
                'category_correct': example.get('category', None) == pred_result.get('category', None),
                'type_correct': example.get('type', None) == pred_result.get('type', None),
                'confidence': pred_result.get('meta', {}).get('confidence', None),
                # infos extras para análise
                'model_confidence': pred_result.get('model_confidence', None),
                'final_category': pred_result.get('category', None),
                'gold_category': example.get('category', None)
            }
            results.append(result)

        return results

    # -----------------------
    # Nova seção 1: avaliação somente do modelo
    # -----------------------
    def avalia_modelo_apenas(self, gold_data):
        """Avalia apenas as previsões do modelo (se disponível)."""
        if not self.model_loaded or self.model_estimator is None:
            print("[Avaliador] Modelo não carregado — pulando avalia_modelo_apenas.")
            return None

        y_true = []
        y_pred = []
        probs = []
        errors = []

        estimator = self.model_estimator

        for example in gold_data:
            text = example['raw_text']
            true_cat = example.get('category', None)
            # Previsão
            try:
                pred = estimator.predict([text])[0]
            except Exception as e:
                print(f"[Avaliador] Erro ao prever com o modelo para texto '{text}': {e}")
                pred = None

            prob = None
            if hasattr(estimator, "predict_proba") and pred is not None:
                try:
                    proba = estimator.predict_proba([text])[0]
                    classes = list(estimator.classes_)
                    if pred in classes:
                        prob = float(proba[classes.index(pred)])
                    else:
                        prob = float(max(proba))
                except Exception as e:
                    prob = None

            y_true.append(true_cat)
            y_pred.append(pred)
            probs.append(prob)

            if true_cat != pred:
                errors.append({
                    'text': text,
                    'true_category': true_cat,
                    'pred_category': pred,
                    'pred_prob': prob
                })

        # Métricas (multi-classe, weighted)
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted', zero_division=0)
        # matriz de confusão
        labels = sorted(list(set([c for c in y_true if c is not None])))
        try:
            cm = confusion_matrix(y_true, y_pred, labels=labels)
            df_cm = pd.DataFrame(cm, index=labels, columns=labels)
        except Exception:
            df_cm = None

        # salvar CSV detalhado
        df_details = pd.DataFrame([{
            'text': ex['raw_text'],
            'gold_category': ex.get('category', None),
            'pred_category': p,
            'pred_prob': prob
        } for ex, p, prob in zip(gold_data, y_pred, probs)])
        df_details.to_csv('data/avaliacao/evaluation_model_only.csv', index=False, encoding='utf-8')

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'errors': errors,
            'confusion_matrix': df_cm,
            'details_csv': 'data/avaliacao/evaluation_model_only.csv'
        }

    # -----------------------
    # Helper e relatório geral (expandido)
    # -----------------------
    def _compare_amounts(self, true_amount, pred_amount):
        """Compara valores monetários com tolerância"""
        if true_amount is None and pred_amount is None:
            return True
        if true_amount is None or pred_amount is None:
            return False
        return abs(true_amount - pred_amount) <= 0.01

    def generate_report(self, gold_data):
        """Gera relatório completo de avaliação, agora incluindo seção modelo e híbrida."""
        print("="*60)
        print("RELATÓRIO DE AVALIAÇÃO DO EXTRATOR (estático, modelo, híbrido)")
        print("="*60)

        # Avaliação por campo (rule-based)
        amount_metrics = self.avalia_extracao_valor(gold_data)
        category_metrics = self.avalia_extracao_categoria(gold_data)

        print(f"\n📊 EXTRAÇÃO DE VALORES MONETÁRIOS (rule-based):")
        print(f"   Precisão: {amount_metrics['precision']:.3f}")
        print(f"   Recall: {amount_metrics['recall']:.3f}")
        print(f"   F1-Score: {amount_metrics['f1_score']:.3f}")
        print(f"   Acurácia: {amount_metrics['accuracy']:.3f}")
        print(f"   Erros numéricos: {len(amount_metrics['numerical_errors'])}")

        print(f"\n🏷️  EXTRAÇÃO DE CATEGORIAS (rule-based):")
        print(f"   Precisão: {category_metrics['precision']:.3f}")
        print(f"   Recall: {category_metrics['recall']:.3f}")
        print(f"   F1-Score: {category_metrics['f1_score']:.3f}")
        print(f"   Acurácia: {category_metrics['accuracy']:.3f}")
        print(f"   Erros de categoria: {len(category_metrics['errors'])}")

        # Avaliação completa (híbrida via aplica_extrator)
        full_results = self.avalia_pipeline_completo(gold_data)
        amount_accuracy = sum(1 for r in full_results if r['amount_correct']) / len(full_results)
        category_accuracy = sum(1 for r in full_results if r['category_correct']) / len(full_results)
        type_accuracy = sum(1 for r in full_results if r['type_correct']) / len(full_results)
        avg_confidence = np.mean([r['confidence'] for r in full_results])

        print(f"\n🎯 ACURÁCIA POR CAMPO (aplica_extrator):")
        print(f"   Valores: {amount_accuracy:.1%}")
        print(f"   Categorias: {category_accuracy:.1%}")
        print(f"   Tipos: {type_accuracy:.1%}")
        print(f"   Confiança média: {avg_confidence:.3f}")

        print(f"\n📈 RESUMO:")
        print(f"   Total de exemplos avaliados: {len(gold_data)}")

        amount_ok = amount_accuracy >= 0.95
        category_ok = category_accuracy >= 0.80

        print(f"   ✅ Valores ≥95%: {'SIM' if amount_ok else 'NÃO'}")
        print(f"   ✅ Categorias ≥80%: {'SIM' if category_ok else 'NÃO'}")
        if amount_ok and category_ok:
            print("\n🎉 CRITÉRIOS DE ACEITAÇÃO ATENDIDOS!")
        else:
            print("\n⚠️  CRITÉRIOS DE ACEITAÇÃO NÃO ATENDIDOS")

        # Salva resultados detalhados em CSV (pipeline original)
        df_results = pd.DataFrame(full_results)
        df_results.to_csv('data/avaliacao/evaluation_results.csv', index=False, encoding='utf-8')
        print(f"\n💾 Resultados detalhados (aplica_extrator) salvos em 'data/avaliacao/evaluation_results.csv'")

        # -----------------------
        # Seção nova 1: avaliação do modelo apenas
        # -----------------------
        model_only_report = None
        if self.model_loaded:
            print("\n\n🔎 AVALIAÇÃO (SEÇÃO) 1 — MODELO APENAS")
            model_only_report = self.avalia_modelo_apenas(gold_data)
            if model_only_report is not None:
                print(f"   Acurácia (modelo): {model_only_report['accuracy']:.3f}")
                print(f"   Precisão (modelo): {model_only_report['precision']:.3f}")
                print(f"   Recall (modelo): {model_only_report['recall']:.3f}")
                print(f"   F1-score (modelo): {model_only_report['f1_score']:.3f}")
                if model_only_report.get('confusion_matrix') is not None:
                    print("   Matriz de confusão (modelo) disponível como DataFrame no relatório retornado.")
                print(f"   Erros (modelo): {len(model_only_report['errors'])}")
                print(f"   CSV detalhado salvo em: {model_only_report['details_csv']}")
        else:
            print("\n\n🔎 AVALIAÇÃO (SEÇÃO) 1 — MODELO APENAS: SKIPPED (modelo não carregado)")



        # Retornar um dicionário consolidado
        return {
            'amount_metrics': amount_metrics,
            'category_metrics_rule_based': category_metrics,
            'pipeline_summary': {
                'amount_accuracy': amount_accuracy,
                'category_accuracy': category_accuracy,
                'type_accuracy': type_accuracy,
                'avg_confidence': avg_confidence,
                'meets_criteria': amount_ok and category_ok
            },
            'model_only_report': model_only_report,
        }


def main():
    """Executa avaliação completa"""

    # Inicializa extrator (seu extrator pode ser construído com CategoryModel injetado se desejar)
    extrator = ExtratorFinanceiro()  
    avaliador = ExtratorFinanceiroAvaliador(extrator)

    # Carrega dados de teste
    try:
        gold_data = avaliador.load_gold_data('data/sample_data.jsonl')
        print(f"Carregados {len(gold_data)} exemplos para avaliação")
    except FileNotFoundError:
        print("Erro: arquivo 'data/sample_data.jsonl' não encontrado!")
        return

    # Executa avaliação
    results = avaliador.generate_report(gold_data)

    return results

if __name__ == "__main__":
    main()
