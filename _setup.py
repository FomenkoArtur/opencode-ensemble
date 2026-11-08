# _setup.py
import os
from pathlib import Path

def w(path, content):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  Создан {path}")

# ---------------- bayesian.py ----------------
w("ensemble/bayesian.py", '''import json
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
''')

# ---------------- calibration.py ----------------
w("ensemble/calibration.py", '''import json
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
''')

# ---------------- meta_router.py ----------------
w("ensemble/meta_router.py", '''import json
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
''')

# ---------------- visual_diagnose.py ----------------
w("ensemble/visual_diagnose.py", '''import sys
from pathlib import Path

def main():
    diag = Path("diagnose.py")
    if not diag.exists():
        print("diagnose.py не найден, визуальная диагностика пропущена")
        return 0
    import subprocess
    p = subprocess.run([sys.executable, "diagnose.py"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(p.stdout)
    if p.returncode != 0:
        print("Визуальная диагностика показала проблемы")
        return 2
    print("Визуальная диагностика: всё OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
''')

# ---------------- run_ensemble.py ----------------
w("ensemble/run_ensemble.py", '''import argparse, json, os, re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bayesian import ModelWeights
from calibration import Calibrator
from meta_router import MetaRouter

ENSEMBLE_ROOT = Path(__file__).resolve().parents[1]
WORK = ENSEMBLE_ROOT / ".ensemble"

def _find_opencode():
    for name in ("opencode", "opencode.cmd", "opencode.exe"):
        p = shutil.which(name)
        if p: return p
    return "opencode"

OC = _find_opencode()
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
MSG = "Read TASK.md and carry it out completely. Edit only files inside this directory."

PERSONAS = [
    "Сначала продумай решение, запиши краткий план в PLAN.md, затем реализуй.",
    "Сначала внимательно прочитай тесты приёмки и существующий код, затем делай минимальные точные правки.",
    "Сначала проверь физическую и математическую корректность, потом пиши код.",
    "Работай маленькими шагами: после каждого шага запускай тесты и исправляй.",
]

TEMPLATE = """# Роль
Ты — инженер. {persona}

# Спецификация
{spec}

# Приёмка
Прохождение тестов `{test}`. Запускай: `python -m pytest {test} -q --tb=short`.
Папки acceptance и specs НЕ ИЗМЕНЯЙ. Не делай git commit.
"""

VISUAL_REFINE = """# Роль
Ты — старший инженер. Твои изменения прошли unit-тесты, но визуальная диагностика показала проблемы.
# Отчёт {report}
# 
# text
# # Что делать
# Усиль штрафы за статику и ложные срабатывания в конфигурации.
# Затем снова запусти `python -m pytest {test} -q --tb=short`.
# """
# 
# JUDGE = """# Роль
# Ты — рецензент. Сравни решения в CANDS/ (diff+log). Спецификация — SPEC.md.
# # Результат
# Запиши ТОЛЬКО JSON в `{out}`:
# {{"ranking": ["имя_лучшего","...","имя_худшего"],
#   "best_ideas": [{{"from":"имя","what":"что перенять"}}],
#   "notes":"кратко"}}
# Имена: {names}
# """
# 
# FUSE = """# Роль
# Ведущий инженер. Объедини решение-победителя с идеями рецензентов.
# {ideas}
# Приёмка: `python -m pytest {test} -q --tb=short` должна остаться зелёной.
# """
# 
# REFINER = """# Роль
# Старший инженер. Победитель уже прошёл приёмку. Рецензенты указали идеи: {ideas}.
# Перенеси их, не ломая тесты. `python -m pytest {test} -q --tb=short` должна быть зелёной.
# """
# 
# def sh(cmd, cwd, timeout=None):
#     try:
#         p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=NO_WINDOW)
#         return p.returncode, (p.stdout or "") + (p.stderr or "")
#     except subprocess.TimeoutExpired:
#         return 124, f"TIMEOUT {timeout}s"
# 
# def git(*a, cwd): return sh(["git", *a], cwd)
# def safe(name): return re.sub(r"\\W+", "_", name.split("/")[-1])
# 
# def make_worktree(project, wp, name, base):
#     path = WORK / wp / name
#     git("worktree", "remove", "--force", str(path), cwd=project)
#     git("branch", "-D", f"ens/{wp}/{name}", cwd=project)
#     git("worktree", "prune", cwd=project)
#     rc, out = git("worktree", "add", "-b", f"ens/{wp}/{name}", str(path), base, cwd=project)
#     if rc: raise RuntimeError(out)
#     return path
# 
# def _ensure_files(project, wt):
#     for folder in ("specs", "acceptance"):
#         src = ENSEMBLE_ROOT / folder
#         dst = wt / folder
#         if not src.exists(): continue
#         dst.mkdir(parents=True, exist_ok=True)
#         for f in src.iterdir():
#             if f.is_file(): shutil.copy2(f, dst / f.name)
# 
# def ask(project, model, text, cwd, tag, timeout):
#     (cwd / "TASK.md").write_text(text, encoding="utf-8")
#     cmd = [OC, "run", "-m", model, "--auto", "--format", "json", "--title", tag, MSG]
#     try:
#         p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=NO_WINDOW)
#         rc, out = p.returncode, (p.stdout or "") + (p.stderr or "")
#     except subprocess.TimeoutExpired:
#         rc, out = 124, "TIMEOUT"
#     (cwd / f"_oc_{tag}.log").write_text(out[-20000:], encoding="utf-8")
#     return rc
# 
# def verify(wt, test, timeout=1800):
#     rc, out = sh([sys.executable, "-m", "pytest", test, "-q", "--tb=short", "-p", "no:cacheprovider"], cwd=wt, timeout=timeout)
#     num = lambda w: int(m.group(1)) if (m := re.search(rf"(\\d+) {w}", out)) else 0
#     passed, failed, errors = num("passed"), num("failed"), num(r"errors?")
#     return dict(ok=(rc == 0 and passed > 0), passed=passed, failed=failed, errors=errors, score=passed - failed - errors, tail=out[-3500:])
# 
# def run_visual_diagnostics(wt, timeout=180):
#     diag = ENSEMBLE_ROOT / "ensemble" / "visual_diagnose.py"
#     if not diag.exists(): return "", True
#     try:
#         p = subprocess.run([sys.executable, str(diag)], cwd=wt, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
#         if p.returncode != 0: return f"Ошибка: {(p.stderr or p.stdout)[-1000:]}", False
#         return p.stdout, (p.returncode == 0)
#     except: return "Таймаут", True
# 
# def commit(wt, msg):
#     git("add", "-A", "--", ".", ":(exclude)TASK.md", ":(exclude)PLAN.md", ":(exclude)_oc_*.log", ":(exclude)diagnostics", cwd=wt)
#     git("-c", "user.name=ens", "-c", "user.email=ens@local", "commit", "-q", "--allow-empty", "-m", msg, cwd=wt)
# 
# def candidate(project, args, base, spec, idx, model):
#     name = safe(model)
#     wt = make_worktree(project, args.wp, name, base)
#     _ensure_files(project, wt)
#     first = TEMPLATE.format(persona=PERSONAS[idx % len(PERSONAS)], spec=spec, test=args.test)
#     task, res, report, visual_ok = first, {}, "", True
#     r = -1
#     for r in range(args.rounds + 1):
#         rc = ask(project, model, task, wt, f"{args.wp}-{name}-r{r}", args.timeout)
#         _ensure_files(project, wt)
#         res = verify(wt, args.test)
#         if res["passed"] == 0 and res["failed"] == 0 and res["errors"] == 0:
#             print(f"[{args.wp}] {name} r{r}: pytest упал (rc={rc})", flush=True)
#         else:
#             print(f"[{args.wp}] {name} r{r}: unit {res['passed']}p/{res['failed']}f", flush=True)
#         if not res["ok"]:
#             task = first + f"\\n\\n# Тесты не прошли\\n```\\n{res['tail']}\\n```\\nИсправь код."
#             continue
#         report, visual_ok = run_visual_diagnostics(wt)
#         if visual_ok: break
#         if r < args.rounds:
#             task = VISUAL_REFINE.format(report=report, test=args.test)
#             continue
#         break
#     commit(wt, f"{args.wp}: candidate {name}")
#     return dict(name=name, model=model, rounds_used=r, visual_ok=visual_ok, visual_report=report[-2000:] if report else "", **{k: v for k, v in res.items() if k != "tail"}, tail=res["tail"])
# 
# def stage_gen(project, args, cfg):
#     WORK.mkdir(exist_ok=True)
#     base = git("rev-parse", "--abbrev-ref", "HEAD", cwd=project)[1].strip()
#     spec = Path(args.spec).read_text(encoding="utf-8")
#     models = args.models.split(",") if args.models else cfg.get("generators", [])
#     history = json.loads((ENSEMBLE_ROOT / "history.json").read_text("utf-8")) if (ENSEMBLE_ROOT / "history.json").exists() else []
#     router = MetaRouter(models)
#     if len(history) >= 6: router.fit()
#     with ThreadPoolExecutor(args.parallel) as ex:
#         futs = [ex.submit(candidate, project, args, base, spec, i, m) for i, m in enumerate(models)]
#         cands = []
#         for m, f in zip(models, futs):
#             try: cands.append(f.result())
#             except Exception as e: print("FAILED", m, e)
#     (WORK / args.wp).mkdir(parents=True, exist_ok=True)
#     (WORK / args.wp / "results.json").write_text(json.dumps(dict(base=base, cands=cands), ensure_ascii=False, indent=1), "utf-8")
#     mw = ModelWeights(ENSEMBLE_ROOT / "weights.json")
#     for c in cands:
#         mw.update(c["name"], c.get("ok", False) and c.get("visual_ok", False))
#         router.add({}, c["name"], c["score"])
#     for c in sorted(cands, key=lambda c: (c.get("visual_ok", False), c.get("score", 0)), reverse=True):
#         print(f"  {c['name']:35s} unit_ok={c.get('ok')} visual_ok={c.get('visual_ok')} score={c.get('score')}", flush=True)
# 
# if __name__ == "__main__":
#     ap = argparse.ArgumentParser()
#     ap.add_argument("stage", choices=["gen", "all"])
#     ap.add_argument("--project", required=True)
#     ap.add_argument("--wp", required=True)
#     ap.add_argument("--spec", required=True)
#     ap.add_argument("--test", required=True)
#     ap.add_argument("--config", default="models.json")
#     ap.add_argument("--models")
#     ap.add_argument("--rounds", type=int, default=2)
#     ap.add_argument("--parallel", type=int, default=2)
#     ap.add_argument("--timeout", type=int, default=2400)
#     a = ap.parse_args()
#     project = Path(a.project).resolve()
#     cfg_path = ENSEMBLE_ROOT / a.config
#     cfg = json.loads(cfg_path.read_text("utf-8")) if cfg_path.exists() else {}
#     if a.stage in ("gen", "all"): stage_gen(project, a, cfg)
# ''')
#
# # ---------------- models.json ----------------
# w("models.json", '''{
#   "generators": ["opencode/deepseek-v4.1-flash-free", "opencode/glm-5.3-flash-free", "opencode/mimo-v2.6-flash-free", "opencode/nemotron-3.5-super-vl-free"]
# }
# ''')
#
# # ---------------- requirements.txt ----------------
# w("requirements.txt", '''numpy>=1.26
# scikit-learn>=1.4
# pytest>=8.0
# ''')
#
# # ---------------- .gitignore ----------------
# w(".gitignore", '''.venv/
# .ensemble/
# __pycache__/
# *.pyc
# .idea/
# *.log
# ''')
#
# print("\\nВсе файлы успешно созданы!")