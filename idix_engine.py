import numpy as np

# ============================================================
# CORE DIMENSIONS
# ============================================================

CORE_DIMENSIONS = [
    "thinking",
    "execution",
    "risk",
    "motivation",
    "team",
    "commercial",
]


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _extract_vector(data: dict) -> np.ndarray:
    """
    Extract a 6D vector from archetype data.

    Supports either:
      - "vector": { ... }
      - "signature": { ... }

    Falls back safely to zeros if missing.
    """
    vec_dict = data.get("vector") or data.get("signature") or {}
    return np.array([float(vec_dict.get(dim, 0.0)) for dim in CORE_DIMENSIONS])


# ============================================================
# SCORE NORMALISATION
# ============================================================

def normalize_scores(answers: dict) -> dict:
    """
    Convert raw Likert answers (1–5) into 0–100 scores per dimension.

    answers format:
    {
        "question text": {
            "value": 1–5,
            "dimension": "thinking" | ...,
            "reverse": True/False
        }
    }
    """
    dimension_values = {dim: [] for dim in CORE_DIMENSIONS}

    for _, meta in answers.items():
        val = meta.get("value", 3)
        dim = meta.get("dimension", "thinking")
        reverse = meta.get("reverse", False)

        # reverse-scoring: 1 ↔ 5
        if reverse:
            val = 6 - val

        if dim in dimension_values:
            dimension_values[dim].append(val)

    final_scores = {}
    for dim, vals in dimension_values.items():
        if not vals:
            # neutral default if dimension has no items
            final_scores[dim] = 50.0
        else:
            avg = sum(vals) / len(vals)  # 1–5
            # map 1–5 → 0–100
            final_scores[dim] = (avg - 1) / 4 * 100

    return final_scores


# ============================================================
# ARCHETYPE MATCHING
# ============================================================

def determine_archetype(final_scores: dict, archetypes: dict):
    """
    Find the closest archetype in 6D space using Euclidean distance.

    Returns:
        (primary_name, archetype_data_dict)
    """
    if not archetypes:
        return None, {}

    user_vec = np.array([final_scores[dim] for dim in CORE_DIMENSIONS])

    best_name = None
    best_dist = float("inf")

    for name, data in archetypes.items():
        vec = _extract_vector(data)
        dist = np.linalg.norm(user_vec - vec)

        if dist < best_dist:
            best_dist = dist
            best_name = name

    return best_name, archetypes.get(best_name, {})


# ============================================================
# DISTANCE → ENERGY (OPTIONAL)
# ============================================================

def _distance_to_energy(distance: float, temp: float = 60.0) -> float:
    """
    Softmax-style transform: lower distance → higher weight.

    temp (temperature) controls how "sharp" the energy curve is.
    """
    return float(np.exp(-distance / temp))


def compute_archetype_distances(final_scores: dict, archetypes: dict) -> dict:
    """
    Utility for diagnostics / analytics.

    Returns:
        {
          "euclidean": {name: distance, ...},
          "energy": {name: energy_weight, ...}
        }
    """
    user_vec = np.array([final_scores[dim] for dim in CORE_DIMENSIONS])

    euclidean = {}
    energy = {}

    for name, data in archetypes.items():
        vec = _extract_vector(data)
        dist = np.linalg.norm(user_vec - vec)
        euclidean[name] = float(dist)
        energy[name] = _distance_to_energy(dist)

    return {"euclidean": euclidean, "energy": energy}


# ============================================================
# MONTE CARLO IDENTITY SIMULATION
# ============================================================

def monte_carlo_probabilities(
    final_scores: dict,
    archetypes: dict,
    trials: int = 4000,
    noise: float = 4.0,
):
    """
    Run many noisy simulations of the user's 6D profile to estimate:

      - probability of each archetype
      - stability of the primary archetype
      - shadow archetype (second-strongest)

    Returns:
        probs: {archetype_name: probability_percentage}
        stability: float (% for primary archetype)
        shadow: (shadow_name, shadow_pct)
    """
    if not archetypes:
        return {}, 0.0, ("None", 0.0)

    user_vec = np.array([final_scores[dim] for dim in CORE_DIMENSIONS])

    arche_vecs = {
        name: _extract_vector(data)
        for name, data in archetypes.items()
    }

    counts = {name: 0 for name in archetypes.keys()}
    arche_names = list(archetypes.keys())

    for _ in range(trials):
        # Add Gaussian noise around the user's true vector
        noisy_vec = user_vec + np.random.normal(0, noise, size=len(CORE_DIMENSIONS))

        # Find closest archetype to this noisy profile
        best_name = None
        best_dist = float("inf")

        for name in arche_names:
            dist = np.linalg.norm(noisy_vec - arche_vecs[name])
            if dist < best_dist:
                best_dist = dist
                best_name = name

        counts[best_name] += 1

    # Convert counts → percentages
    probs = {name: (count / trials) * 100 for name, count in counts.items()}

    # Primary archetype = highest probability
    primary_name = max(probs, key=probs.get)
    stability = probs[primary_name]

    # Shadow archetype = second highest (if exists)
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_probs) > 1:
        shadow_name, shadow_pct = sorted_probs[1]
    else:
        shadow_name, shadow_pct = primary_name, stability

    return probs, stability, (shadow_name, shadow_pct)
