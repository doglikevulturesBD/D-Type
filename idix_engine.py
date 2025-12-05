import numpy as np

# ============================================================
# CORE DIMENSIONS FOR D-TYPE
# ============================================================

CORE_DIMENSIONS = [
    "clinical_decision_style",
    "response_tempo",
    "risk_orientation",
    "team_communication",
    "stress_handling",
    "learning_adaptation",
]


# ============================================================
# SCORE NORMALISATION (LIKERT 1–5 → 0–1)
# ============================================================

def normalize_scores(answers: dict) -> dict:
    """
    Convert raw Likert answers (1–5) into 0–1 scores per dimension.

    answers format:
    {
        <question_id or text>: {
            "value": 1–5,
            "dimension": "clinical_decision_style" | ...,
            "reverse": True/False
        },
        ...
    }
    """
    dimension_values = {dim: [] for dim in CORE_DIMENSIONS}

    for _, meta in answers.items():
        dim = meta.get("dimension")
        if dim not in CORE_DIMENSIONS:
            continue

        val = meta.get("value", 3)
        reverse = meta.get("reverse", False)

        # reverse-scoring: 1 ↔ 5
        if reverse:
            val = 6 - val

        dimension_values[dim].append(val)

    final_scores = {}
    for dim, vals in dimension_values.items():
        if not vals:
            # Neutral default (midpoint 0.5) if dimension has no items
            final_scores[dim] = 0.5
        else:
            avg = sum(vals) / len(vals)  # 1–5
            # map 1–5 → 0–1
            final_scores[dim] = (avg - 1.0) / 4.0

    return final_scores


# ============================================================
# ARCHETYPE HELPERS
# ============================================================

def _build_archetype_vector(archetype: dict) -> np.ndarray:
    """
    Build an 'ideal' behaviour vector for the archetype in 0–1 space.

    Convention:
      - Primary dimensions: 1.0
      - Secondary:          0.7
      - Tertiary:           0.4

    This describes the PATTERN of each archetype.
    """
    primary = set(archetype.get("primary_dimensions", []))
    secondary = set(archetype.get("secondary_dimensions", []))
    tertiary = set(archetype.get("tertiary_dimensions", []))

    vec = []
    for dim in CORE_DIMENSIONS:
        if dim in primary:
            vec.append(1.0)
        elif dim in secondary:
            vec.append(0.7)
        elif dim in tertiary:
            vec.append(0.4)
        else:
            # if somehow not listed, treat as neutral-ish
            vec.append(0.5)
    return np.array(vec, dtype=float)


def _extract_weight_vector(archetype: dict) -> np.ndarray:
    """
    Extract numerical weights per dimension from archetype["dimension_weights"].

    Falls back to 0.0 if a dimension is missing (should not happen if JSON is correct).
    """
    w_dict = archetype.get("dimension_weights", {})
    return np.array([float(w_dict.get(dim, 0.0)) for dim in CORE_DIMENSIONS], dtype=float)


# ============================================================
# WEIGHTED DISTANCE & SIMILARITY (PHYSICS-STYLE)
# ============================================================

def _weighted_distance(user_vec: np.ndarray,
                       arche_vec: np.ndarray,
                       weight_vec: np.ndarray) -> float:
    """
    Weighted Euclidean distance.
    Lower distance = closer behavioural match.
    """
    diff = user_vec - arche_vec
    return float(np.sqrt(np.sum(weight_vec * (diff ** 2))))


def _weighted_similarity(user_vec: np.ndarray,
                         arche_vec: np.ndarray,
                         weight_vec: np.ndarray) -> float:
    """
    Weighted dot-product similarity.
    Higher similarity = stronger alignment with archetype pattern.
    """
    return float(np.sum(weight_vec * user_vec * arche_vec))


def _hybrid_score(user_vec: np.ndarray,
                  arche_vec: np.ndarray,
                  weight_vec: np.ndarray) -> float:
    """
    Hybrid 'attraction' score combining similarity and distance:

        score = similarity - distance

    Higher score → better archetype fit.
    """
    dist = _weighted_distance(user_vec, arche_vec, weight_vec)
    sim = _weighted_similarity(user_vec, arche_vec, weight_vec)
    return sim - dist


# ============================================================
# PRIMARY ARCHETYPE MATCHING
# ============================================================

def determine_archetype(final_scores: dict, archetypes: dict):
    """
    Determine the best-fitting D-Type archetype.

    final_scores: normalised 0–1 dict from normalize_scores()
    archetypes:   dict loaded from archetypes.json

    Returns:
        (primary_name, archetype_data_dict)
    """
    if not archetypes:
        return None, {}

    user_vec = np.array([final_scores.get(dim, 0.5) for dim in CORE_DIMENSIONS], dtype=float)

    best_name = None
    best_score = -1e9

    for name, data in archetypes.items():
        arche_vec = _build_archetype_vector(data)
        w_vec = _extract_weight_vector(data)

        score = _hybrid_score(user_vec, arche_vec, w_vec)

        if score > best_score:
            best_score = score
            best_name = name

    return best_name, archetypes.get(best_name, {})


# ============================================================
# DIAGNOSTIC DISTANCES (OPTIONAL)
# ============================================================

def compute_archetype_distances(final_scores: dict, archetypes: dict) -> dict:
    """
    For diagnostics / analytics / debugging.

    Returns:
      {
        "distance": {name: d, ...},
        "similarity": {name: s, ...},
        "hybrid": {name: score, ...}
      }
    """
    user_vec = np.array([final_scores.get(dim, 0.5) for dim in CORE_DIMENSIONS], dtype=float)

    distances = {}
    similarities = {}
    hybrids = {}

    for name, data in archetypes.items():
        arche_vec = _build_archetype_vector(data)
        w_vec = _extract_weight_vector(data)

        d = _weighted_distance(user_vec, arche_vec, w_vec)
        s = _weighted_similarity(user_vec, arche_vec, w_vec)
        h = s - d

        distances[name] = d
        similarities[name] = s
        hybrids[name] = h

    return {
        "distance": distances,
        "similarity": similarities,
        "hybrid": hybrids,
    }


# ============================================================
# MONTE CARLO PROBABILITIES (SHADOW ARCHETYPE, STABILITY)
# ============================================================

def monte_carlo_probabilities(
    final_scores: dict,
    archetypes: dict,
    trials: int = 4000,
    noise: float = 0.08,
):
    """
    Run many noisy simulations of the user's 6D profile to estimate:

      - probability of each archetype
      - stability of the primary archetype
      - shadow archetype (second-strongest)

    final_scores: normalised 0–1 scores
    archetypes:   dict from archetypes.json
    trials:       number of Monte Carlo samples
    noise:        std dev of Gaussian noise in 0–1 space

    Returns:
        probs:    {archetype_name: probability_percentage}
        stability: float (% for primary archetype)
        shadow:   (shadow_name, shadow_pct)
    """
    if not archetypes:
        return {}, 0.0, ("None", 0.0)

    user_vec = np.array([final_scores.get(dim, 0.5) for dim in CORE_DIMENSIONS], dtype=float)

    # Pre-build archetype vectors & weights for speed
    arche_data = {}
    for name, data in archetypes.items():
        arche_vec = _build_archetype_vector(data)
        w_vec = _extract_weight_vector(data)
        arche_data[name] = (arche_vec, w_vec)

    counts = {name: 0 for name in archetypes.keys()}
    arche_names = list(archetypes.keys())

    for _ in range(trials):
        # Add Gaussian noise around the user's true vector
        noisy_vec = user_vec + np.random.normal(0.0, noise, size=len(CORE_DIMENSIONS))

        # Clip to [0, 1] to avoid runaway values
        noisy_vec = np.clip(noisy_vec, 0.0, 1.0)

        best_name = None
        best_score = -1e9

        for name in arche_names:
            arche_vec, w_vec = arche_data[name]
            score = _hybrid_score(noisy_vec, arche_vec, w_vec)

            if score > best_score:
                best_score = score
                best_name = name

        counts[best_name] += 1

    # Convert counts → percentages
    probs = {name: (count / trials) * 100.0 for name, count in counts.items()}

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
