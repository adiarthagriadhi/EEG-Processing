from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path=None):
    path = Path(path) if path else ROOT / "config.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg["_root"] = path.resolve().parent
    return cfg


@dataclass
class Participant:
    """Lokasi file mentah, hasil antara, dan keputusan satu partisipan."""
    pid: str
    cfg: dict

    def _p(self, key):
        return self.cfg["_root"] / self.cfg["paths"][key]

    @property
    def raw_dir(self):
        return self._p("raw") / self.pid

    @property
    def deriv_dir(self):
        d = self._p("derivatives") / self.pid
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def report_dir(self):
        d = self._p("reports")
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def results_dir(self):
        d = self._p("results")
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def decisions_path(self):
        return self._p("decisions") / f"{self.pid}.yaml"

    def _find(self, *patterns):
        hits = []
        for pat in patterns:
            hits += [p for p in self.raw_dir.glob("*") if p.match(pat)]
        hits = sorted(set(hits))
        if len(hits) != 1:
            raise FileNotFoundError(f"{self.pid}: harap tepat 1 file untuk {patterns} di "
                                    f"{self.raw_dir}, ditemukan {[h.name for h in hits]}")
        return hits[0]

    @property
    def baseline_edf(self):
        return self._find("*Baseline*.EDF", "*Baseline*.edf")

    @property
    def trial_edf(self):
        return self._find("*Trial*.EDF", "*Trial*.edf")

    @property
    def video(self):
        return self._find("*.webm", "*.mp4")

    def out(self, name):
        return self.deriv_dir / name

    def decisions(self):
        if self.decisions_path.exists():
            with open(self.decisions_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def save_decisions(self, dec):
        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.decisions_path, "w") as f:
            yaml.safe_dump(dec, f, sort_keys=False, allow_unicode=True)
