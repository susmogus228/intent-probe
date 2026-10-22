"""Versioned controlled synthetic profiles; not observations from real people."""
import hashlib
import json
from itertools import product
import numpy as np

from .domain import REAL_VALUES, QUESTION_IDS, utility, feasible_for


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def generate_profiles(seed=42, train_count=300, validation_count=80, test_count=120):
    rng = np.random.default_rng(seed)
    result = []
    complete = [dict(zip(QUESTION_IDS, values)) for values in product(*(REAL_VALUES[q] for q in QUESTION_IDS))]
    pool = [complete[i] for i in rng.permutation(len(complete))]
    if min(train_count, validation_count, test_count) < 1 or train_count + validation_count + test_count > len(pool):
        raise ValueError("Requested split sizes exceed the 540 unique preference-vector pool")
    for split, count in (("train", train_count), ("validation", validation_count), ("test", test_count)):
        for index in range(count):
            condition = ("in_distribution", "preference_shift", "answer_noise")[index % 3] if split == "test" else "in_distribution"
            values = pool.pop()
            identifier = "profile-" + sha256(values)[:16]
            family = "interaction" if condition == "preference_shift" else str(rng.choice(["balanced", "specialist"]))
            # Weekend profiles intentionally have no feasible brief. Preserve them.
            for variant in ("clean", "uncertain"):
                answers = dict(values)
                if variant == "uncertain":
                    # Train/validation: one unknown answer. Shifted noise: a wrong
                    # hardware answer plus unknown preference, never seen in train.
                    if condition == "answer_noise":
                        answers["hardware"] = "local_gpu" if values["hardware"] == "cpu" else "cpu"
                        answers["goal"] = "unknown"
                    else:
                        answers[str(rng.choice(QUESTION_IDS))] = "unknown"
                result.append({"profile_id": identifier, "variant": variant, "split": split, "condition": condition,
                               "family": family, "hidden": values, "answers": answers})
    return result


def observed_states(record, rng, count=5):
    for _ in range(count):
        ordered = list(rng.permutation(QUESTION_IDS))
        answered = int(rng.integers(0, 5))
        facts = {q: record["answers"][q] for q in ordered[:answered]}
        excluded = []
        if answered < 4 and rng.random() < 0.15:
            excluded = [ordered[answered]]
        yield facts, excluded, int(rng.integers(1, 6))


def training_examples(records, prior, seed=42, states_per_profile=5):
    from .domain import features, QUESTION_COST
    rng = np.random.default_rng(seed)
    rows, labels, groups = [], [], []
    for record in records:
        utilities = utility(record["hidden"], record["family"])
        for facts, excluded, budget in observed_states(record, rng, states_per_profile):
            _, feasible, order = prior.rank(facts)
            if not feasible.any():
                continue
            before = utilities[order[0]]
            for q in QUESTION_IDS:
                if q in facts or q in excluded:
                    continue
                _, after_feasible, after_order = prior.rank(facts | {q: record["answers"][q]})
                after = float(utilities[after_order[0]]) if after_feasible.any() else 0.0
                rows.append(features(prior, facts, excluded, q, budget))
                labels.append(float(after - before - QUESTION_COST))
                groups.append(record["profile_id"])
    return np.asarray(rows, dtype=np.float64), np.asarray(labels), groups
