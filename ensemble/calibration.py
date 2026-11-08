import json
from pathlib import Path
from sklearn.linear_model import LogisticRegression

class Calibrator:
    def __init__(self, path="calibrator.json"):
        self.path = Path(path)
        self.model = LogisticRegression()
        self.fitted = False
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if data.get("fitted"):
                    import numpy as np
                    self.model.coef_ = np.array([data["coef"]])
                    self.model.intercept_ = np.array([data["intercept"]])
                    self.model.classes_ = np.array([0, 1])
                    self.fitted = True
            except Exception: pass

    def fit(self, history):
        X = [[h.get("raw_conf", 0.5)] for h in history]
        y = [1 if h.get("score", 0) > 0 else 0 for h in history]
        if len(set(y)) > 1:
            self.model.fit(X, y)
            self.fitted = True
            data = {"fitted": True, "coef": float(self.model.coef_[0][0]), "intercept": float(self.model.intercept_[0])}
            self.path.write_text(json.dumps(data), encoding="utf-8")
            return True
        return False

    def predict(self, raw_conf):
        if not self.fitted: return raw_conf
        return float(self.model.predict_proba([[raw_conf]])[0][1])
