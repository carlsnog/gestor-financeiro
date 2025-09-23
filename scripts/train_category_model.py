from pathlib import Path
import joblib
import json
import pandas as pd
import os

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from joblib import parallel_backend


DATA_PATH = Path("data/sample_data.jsonl")
OUT_MODEL = Path("modelos/category_model_tfidf_lr.joblib")
MISCLASS_CSV = Path("data/avaliacao/misclassified_after_train.csv")

def load_data(path: Path):
    texts, labels = [], []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            texts.append(obj.get('raw_text', ''))
            labels.append(obj.get('category', None))
    return texts, labels

def ensure_parent(path: Path):
    parent = path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

def main(X, y):
    # 1) Hold-out split (mantém X_test intocado)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )

    tfidf = TfidfVectorizer(ngram_range=(1,1), analyzer="word", min_df=1, max_df=0.8)
    lr = LogisticRegression(C=10, max_iter=1000, class_weight='balanced', solver='lbfgs')

    pipeline = Pipeline([("tfidf", tfidf), ("clf", lr)])

    # 2) Avaliação via CV em X_train
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    with parallel_backend("threading"):
        y_cv_pred = cross_val_predict(pipeline, X_train, y_train, cv=cv, n_jobs=-1)
    print("Cross-validated classification report (sobre X_train):")
    print(classification_report(y_train, y_cv_pred))

    # 3) Treina em X_train e calibra (tudo usando apenas X_train)
    # Não é necessário treinar pipeline aqui antes do CalibratedClassifierCV,
    # pois o calibrador fará o fit clonando o estimator internamente.
    try:
        calibrator = CalibratedClassifierCV(estimator=pipeline, cv=3, method='sigmoid')
    except TypeError:
        calibrator = CalibratedClassifierCV(base_estimator=pipeline, cv=3, method='sigmoid')

    calibrator.fit(X_train, y_train)

    # 4) Avaliação final no hold-out X_test
    y_test_pred = calibrator.predict(X_test)
    print("Relatório final no hold-out test:")
    print(classification_report(y_test, y_test_pred))

    cm = confusion_matrix(y_test, y_test_pred, labels=calibrator.classes_)
    df_cm = pd.DataFrame(cm, index=calibrator.classes_, columns=calibrator.classes_)
    print("Matriz de confusão (hold-out):")
    print(df_cm)

    # Salvar modelo (garantir diretório)
    ensure_parent(OUT_MODEL)
    artifact = {"model": calibrator, "model_type":"tfidf_lr_calibrated", "version":"1.0"}
    joblib.dump(artifact, OUT_MODEL, compress=3)
    print("Modelo salvo em:", OUT_MODEL)

    # Salvar exemplos mal classificados (usar X_test / y_test)
    ensure_parent(MISCLASS_CSV)
    mismatches = []
    for text, true, pred in zip(X_test, y_test, y_test_pred):
        if true != pred:
            mismatches.append({"text": text, "true": true, "pred": pred})
    pd.DataFrame(mismatches).to_csv(MISCLASS_CSV, index=False, encoding='utf-8')
    print(f"Salvei {MISCLASS_CSV} com {len(mismatches)} registros.")

if __name__ == "__main__":
    X_all, y_all = load_data(DATA_PATH)
    main(X_all, y_all)
