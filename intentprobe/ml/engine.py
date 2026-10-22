"""Trusted local artifact loading and observed-state-only question selection."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import hashlib
import json

import joblib
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

from .domain import (CATALOG, QUESTIONS, QUESTION_MAP, QUESTION_IDS, POLICIES,
                     Prior, MODEL_VERSION, GENERATOR_VERSION, feature_names, features, validate,
                     explain_infeasible)
from .simulator import sha256, canonical_bytes


class Engine:
    def __init__(self, artifact_dir: Path):
        self.artifact_dir = Path(artifact_dir)
        model_path = self.artifact_dir / "question_value.joblib"
        metadata_path = self.artifact_dir / "metadata.json"
        if not model_path.is_file() or not metadata_path.is_file():
            raise FileNotFoundError("Trained model artifact is missing. Run python -m intentprobe.ml.train --output artifacts")
        self._metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.constraint_aware = self._metadata["model"].get("objective") == "constraint_aware"
        if self.constraint_aware:
            from .constraints import feature_names_v2, V2_GENERATOR_VERSION
            expected_features = feature_names_v2()
            expected_generator = V2_GENERATOR_VERSION
        else:
            expected_features = feature_names()
            expected_generator = GENERATOR_VERSION
        actual = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if actual != self._metadata["model"]["artifact_sha256"]:
            raise ValueError("Model artifact integrity hash mismatch")
        if self._metadata["dataset"]["catalog_sha256"] != sha256(CATALOG):
            raise ValueError("Model catalog does not match this code version; retrain the model")
        if self._metadata["model"]["feature_names"] != expected_features:
            raise ValueError("Model feature schema does not match this code version")
        if self._metadata["model"]["environment"]["scikit_learn"] != sklearn.__version__:
            raise ValueError("Incompatible scikit-learn version for the trusted model artifact; use the recorded environment or retrain")
        if self._metadata["dataset"]["generator_version"] != expected_generator:
            raise ValueError("Model generator version does not match this code version; retrain")
        # joblib is pickle-based: a matching companion hash is integrity evidence,
        # not authentication. Only locally trained, trusted directories may load.
        with threadpool_limits(limits=1):
            self.estimator = joblib.load(model_path)
        if self.estimator.__class__.__name__ != "ExtraTreesRegressor":
            raise ValueError("Artifact is not the required trained question-value model")
        if self.constraint_aware:
            from .constraints import ConstraintPrior
            self.prior = ConstraintPrior()
        else:
            self.prior = Prior()

    def metadata(self):
        result = deepcopy(self._metadata)
        benchmark_path = self.artifact_dir / "benchmark.json"
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8")) if benchmark_path.is_file() else {}
        matches = (benchmark.get("model_artifact_sha256") == self._metadata["model"]["artifact_sha256"]
                   and benchmark.get("test_records_sha256") == self._metadata["dataset"]["test_records_sha256"])
        result["benchmark"] = benchmark if matches else {}
        result["benchmark_state"] = "ready" if matches else "unavailable: benchmark does not match the loaded model and frozen data"
        result["questions"] = deepcopy(QUESTIONS)
        result["catalog"] = deepcopy(CATALOG)
        return result

    def values(self, facts, excluded, budget, policy):
        return list(self._values(tuple(sorted(facts.items())), tuple(sorted(excluded)), budget, policy))

    @lru_cache(maxsize=20000)
    def _values(self, facts_tuple, excluded, budget, policy):
        facts = dict(facts_tuple)
        available = [q for q in QUESTION_IDS if q not in facts and q not in excluded]
        if not available:
            return []
        if policy == "learned":
            feature_function = features
            if self.constraint_aware:
                from .constraints import features_v2
                feature_function = features_v2
            matrix = np.asarray([feature_function(self.prior, facts, excluded, q, budget) for q in available])
            with threadpool_limits(limits=1):
                gains = self.estimator.predict(matrix)
            return [(q, float(gain)) for q, gain in zip(available, gains)]
        return [(q, self.prior.analytic_gain(facts, q)) for q in available]

    def choose(self, facts, excluded, budget, policy, rng=None):
        validate(facts, excluded, budget, policy)
        _, feasible, _ = self.prior.rank(facts)
        if not feasible.any():
            return None, [], "No feasible brief matches the stated hard constraints. Revise a constraint or stop."
        values = self.values(facts, excluded, budget, policy)
        if budget == 0:
            return None, values, "The question budget is exhausted. Unstated constraints may still affect feasibility."
        if policy == "none":
            return None, values, "The no-clarification baseline stops without asking a question."
        if not values:
            return None, [], "All available questions have been answered or skipped."
        if policy in ("learned", "analytic"):
            selected, gain = max(values, key=lambda pair: pair[1])
            if gain <= 0:
                return None, values, "Estimated decision improvement does not exceed the synthetic question cost. This does not prove the recommendation is correct."
            reason = "Ask the question with the largest estimated reduction in recommendation regret after its simulated cost."
            if self.constraint_aware:
                reason = "Ask the question with the largest estimated reduction in regret plus invalid-recommendation and false-no-feasible penalties, after the synthetic question cost. The output guard does not change this question."
            return selected, values, reason
        if policy == "information_gain":
            selected = max((q for q, _ in values), key=lambda q: self.prior.information_gain(facts, q))
            return selected, values, "Ask the question with highest answer entropy under the finite prior. Entropy is not decision utility."
        if policy == "fixed":
            return values[0][0], values, "Follow the fixed order: time, hardware, experience, domain, goal."
        if rng is None:
            seed = int(hashlib.sha256(canonical_bytes([facts, excluded, budget])).hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
        return str(rng.choice([q for q, _ in values])), values, "Select an admissible question using the reproducible random baseline."

    def inspect(self, facts: dict[str, str], excluded: list[str], budget: int, policy: str):
        from .constraints import constraint_outcome, constraint_status
        selected, values, reason = self.choose(facts, excluded, budget, policy)
        scores, feasible, order = self.prior.rank(facts)
        ranked = []
        for index in order:
            item = CATALOG[int(index)]
            reasons = explain_infeasible(item, facts)
            if feasible[index]:
                if facts.get("domain") == item["domain"]:
                    reasons.append("Matches your stated problem-domain preference.")
                if facts.get("goal") == item["goal"]:
                    reasons.append("Matches your stated desired outcome.")
                reasons.append(f"Estimated scope: {item['weeks']} weeks. Feasible against stated constraints only.")
            ranked.append({"id": item["id"], "title": item["title"], "summary": item["summary"],
                           "fit_score": round(float(scores[index]), 6), "feasible": bool(feasible[index]),
                           "reasons": reasons, "tags": item["tags"], "constraint_status": constraint_status(item, facts)})
        next_question = None
        if selected:
            next_question = deepcopy(QUESTION_MAP[selected])
            next_question.update(reason=reason, estimated_gain=dict(values)[selected])
        return {"ranked_projects": ranked, "next_question": next_question,
                "question_values": [{"question_id": q, "title": QUESTION_MAP[q]["title"], "estimated_gain": gain} for q, gain in values],
                "decision": {"action": "ask" if selected else "stop", "reason": reason},
                "outcome": constraint_outcome(self.prior, facts),
                "model_version": self._metadata["model"]["version"]}
