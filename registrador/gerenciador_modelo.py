import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import joblib
import json
import pandas as pd

# sklearn imports (mesma arquitetura do seu script de treino)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict
from sklearn.metrics import classification_report
from joblib import parallel_backend


# ---------------------------
# ModelManager: responsável apenas por carregar / treinar / salvar
# ---------------------------
class ModelManager:
    """
    Responsabilidade única: gerenciar persistência e (opcionalmente) treinamento do artefato.
    Não faz pré-processamento de texto nem decisão de negócio.
    """
    def __init__(self, model_path: Path = Path("modelos/category_model_tfidf_lr.joblib")):
        self.model_path = Path(model_path)

    def load(self) -> Optional[dict]:
        """Tenta carregar o artefato (dict contendo 'model' por convenção)."""
        if not self.model_path.exists():
            return None
        try:
            artifact = joblib.load(self.model_path)
            return artifact
        except Exception as e:
            print(f"[ModelManager] Erro ao carregar modelo: {e}")
            return None

    def save(self, artifact: dict):
        """Salva artefato (p.ex. {'model': calibrator, ...})."""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(artifact, self.model_path, compress=3)
        print(f"[ModelManager] Artefato salvo em {self.model_path}")

    def train(self,
              data_path: Path,
              out_model_path: Optional[Path] = None,
              test_size: float = 0.2,
              random_state: int = 42) -> Optional[dict]:
        """
        Treina TF-IDF + LogisticRegression + CalibratedClassifierCV.
        Retorna o artefato (dict) ou None se falhar.
        """
        out_model_path = out_model_path or self.model_path
        texts, labels = self._load_data(data_path)
        if not texts:
            print(f"[ModelManager] Sem dados em {data_path}. Abortando treino.")
            return None

        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, stratify=labels, random_state=random_state
        )

        tfidf = TfidfVectorizer(ngram_range=(1, 1), analyzer="word", min_df=1, max_df=0.8)
        lr = LogisticRegression(C=10, max_iter=1000, class_weight='balanced', solver='lbfgs')
        pipeline = Pipeline([("tfidf", tfidf), ("clf", lr)])

        # avaliação CV (opcional, mas útil)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
        with parallel_backend("threading"):
            try:
                y_cv_pred = cross_val_predict(pipeline, X_train, y_train, cv=cv, n_jobs=-1)
                print("[ModelManager] CV report (train):")
                print(classification_report(y_train, y_cv_pred))
            except Exception as e:
                print("[ModelManager] AVISO: cross_val_predict falhou:", e)

        try:
            calibrator = CalibratedClassifierCV(estimator=pipeline, cv=3, method='sigmoid')
        except TypeError:
            calibrator = CalibratedClassifierCV(base_estimator=pipeline, cv=3, method='sigmoid')

        calibrator.fit(X_train, y_train)

        # avaliação hold-out
        try:
            y_test_pred = calibrator.predict(X_test)
            print("[ModelManager] Relatório hold-out (test):")
            print(classification_report(y_test, y_test_pred))
        except Exception:
            pass

        artifact = {"model": calibrator, "model_type": "tfidf_lr_calibrated", "version": "1.0"}
        out_model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(artifact, out_model_path, compress=3)
        print(f"[ModelManager] Modelo treinado e salvo em {out_model_path}")
        return artifact

    def _load_data(self, data_path: Path) -> Tuple[List[str], List[str]]:
        texts, labels = [], []
        if not Path(data_path).exists():
            return texts, labels
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                texts.append(obj.get('raw_text', ''))
                labels.append(obj.get('category', None))
        return texts, labels


# ---------------------------
# CategoryModel: wrapper para previsões
# ---------------------------
class CategoryModel:
    """
    Wrapper mínimo para um estimador calibrado. Responsabilidade:
    - receber texto cru e retornar (categoria, probability)
    - abstrair diferenças de artefato (se salvaram dict com key 'model' ou só o estimator)
    """
    def __init__(self):
        # caminho para o artefato salvo
        MODEL_PATH = Path("modelos/category_model_tfidf_lr.joblib")

        # 1) criar ModelManager e tentar carregar
        mm = ModelManager(model_path=MODEL_PATH)
        artifact = mm.load()
        # espera artefato com chave "model" (conforme seu script), mas tolera estimator diretamente
        if artifact is None:
            raise ValueError("artifact não pode ser None")
        if isinstance(artifact, dict) and "model" in artifact:
            self.estimator = artifact["model"]
        else:
            self.estimator = artifact

        # garantir que existe atributo classes_
        if not hasattr(self.estimator, "classes_"):
            # nada a fazer aqui — previsão pode falhar depois com erro claro
            pass

    def predict(self, text: str) -> Tuple[Optional[str], Optional[float]]:
        """Retorna (categoria, prob) ou (None, None) em caso de erro / modelo ausente."""
        try:
            pred = self.estimator.predict([text])[0]
            prob = None
            if hasattr(self.estimator, "predict_proba"):
                probs = self.estimator.predict_proba([text])[0]
                classes = list(self.estimator.classes_)
                if pred in classes:
                    idx = classes.index(pred)
                    prob = float(probs[idx])
                else:
                    prob = float(max(probs))
            return pred, prob
        except Exception as e:
            print(f"[CategoryModel] Erro na predição: {e}")
            return None, None
