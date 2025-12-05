import json
import random
from idix_engine import determine_archetype

# Load archetypes
with open("data/archetypes.json", "r") as f:
    archetypes = json.load(f)

def random_profile():
    return {
        "thinking": random.uniform(0, 100),
        "execution": random.uniform(0, 100),
        "risk": random.uniform(0, 100),
        "motivation": random.uniform(0, 100),
        "team": random.uniform(0, 100),
        "commercial": random.uniform(0, 100),
    }

N = 5000
counts = {name: 0 for name in archetypes}

for _ in range(N):
    prof = random_profile()
    name, _ = determine_archetype(prof, archetypes)
    counts[name] += 1

print("\n=== ARCHETYPE DISTRIBUTION (5000 simulations) ===\n")
for name, c in sorted(counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{name:15} {c:4d} ({c/N*100:5.2f}%)")
