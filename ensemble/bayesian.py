import json
from pathlib import Path

class ModelWeights:
    def __init__(self, path="weights.json"):
        self.path = Path(path)
        if self.path.exists():
            try: self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception: self.data = {}
        else: self.data = {}

    def update(self, model_name, success):
        if model_name not in self.data: self.data[model_name] = {"alpha": 1.0, "beta": 1.0}
        if success: self.data[model_name]["alpha"] += 1.0
        else: self.data[model_name]["beta"] += 1.0
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def weight(self, model_name):
        d = self.data.get(model_name, {"alpha": 1.0, "beta": 1.0})
        return d["alpha"] / (d["alpha"] + d["beta"])

    def variance(self, model_name):
        d = self.data.get(model_name, {"alpha": 1.0, "beta": 1.0})
        a, b = d["alpha"], d["beta"]
        return (a * b) / ((a + b) ** 2 * (a + b + 1))
