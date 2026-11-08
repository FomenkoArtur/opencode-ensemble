import json
from pathlib import Path
from sklearn.linear_model import Ridge

class MetaRouter:
    def __init__(self, models, path="history.json"):
        self.models = models
        self.path = Path(path)
        self.reg = Ridge(alpha=1.0)
        self.fitted = False
        self.history = []
        if self.path.exists():
            try: self.history = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception: self.history = []
        if len(self.history) >= 6: self.fit()

    def _featurize(self, wp_meta, model_name):
        base = [wp_meta.get("n_tests", 1), wp_meta.get("spec_length", 1000) / 5000,
                int(wp_meta.get("has_physics", False)), int(wp_meta.get("has_gui", False)), int(wp_meta.get("has_rl", False))]
        onehot = [1.0 if m == model_name else 0.0 for m in self.models]
        return base + onehot

    def fit(self):
        X, y = [], []
        for h in self.history:
            X.append(self._featurize(h["wp_meta"], h["name"]))
            y.append(h["score"])
        self.reg.fit(X, y)
        self.fitted = True

    def select(self, wp_meta, top_k=2):
        if not self.fitted: return self.models[:top_k]
        scores = []
        for m in self.models:
            x = self._featurize(wp_meta, m)
            scores.append((m, self.reg.predict([x])[0]))
        scores.sort(key=lambda t: t[1], reverse=True)
        return [m for m, _ in scores[:top_k]]

    def add(self, wp_meta, name, score):
        self.history.append({"wp_meta": wp_meta, "name": name, "score": score})
        self.path.write_text(json.dumps(self.history, indent=2, ensure_ascii=False), encoding="utf-8")
        if len(self.history) >= 6: self.fit()
