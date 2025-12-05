import streamlit as st
import json
import plotly.graph_objects as go

from dtype_engine import (
CORE_DIMENSIONS,
    normalize_scores,
    determine_archetype,
    monte_carlo_probabilities,
)

# ============================================================
# SESSION STATE INITIALISATION
# ============================================================

def init_state():
    defaults = {
        "step": 1,
        "has_results": False,
        "open_archetype": None,
        "answers": {}
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()


# ============================================================
# LOAD CSS
# ============================================================

def load_css():
    try:
        with open("assets/styles.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass

load_css()


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path, default=None):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

questions = load_json("data/questions.json", default=[])
archetypes = load_json("data/archetypes.json", default={})


# ============================================================
# HERO BANNER
# ============================================================

st.markdown("""
<div class="hero-wrapper">
<div class="hero">
<div class="hero-glow"></div>
<div class="hero-particles"></div>
<div class="hero-content">
<h1 class="hero-title">D-TYPE — Clinical Behaviour Archetypes</h1>
<p class="hero-sub">A behavioural model for medical professionals</p>
</div>
</div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# STEP PROGRESS BAR
# ============================================================

step = st.session_state["step"]
labels = {1: "Step 1 of 2 — Clinical Behaviour Questionnaire",
          2: "Step 2 of 2 — Your Clinical Archetype"}

st.markdown(f"### {labels[step]}")
st.progress(step / 2)


# ============================================================
# BUILD ANSWERS FROM STATE
# ============================================================

def get_answers(questions_list):
    answers = {}
    for i, q in enumerate(questions_list):
        key = f"q{i}"
        val = st.session_state["answers"].get(key, 3)

        answers[str(q["id"])] = {
            "value": val,
            "dimension": q["dimension"],
            "reverse": q.get("reverse", False)
        }
    return answers


# ============================================================
# STEP 1 — QUESTIONS
# ============================================================

if step == 1:

    if not questions:
        st.error("No question file found.")
    else:
        st.markdown("""
        <div class="likert-legend">
        <span>1 = Strongly Disagree</span>
        <span>5 = Strongly Agree</span>
        </div>
        """, unsafe_allow_html=True)

        for i, q in enumerate(questions):
            st.markdown(f"<p><b>{q['question']}</b></p>", unsafe_allow_html=True)

            # Slider retains value WITHOUT resetting page
            st.session_state["answers"][f"q{i}"] = st.slider(
                "", 1, 5,
                st.session_state["answers"].get(f"q{i}", 3),
                key=f"slider_{i}"
            )

            st.markdown("<hr>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        def reset():
            st.session_state["answers"] = {}
            st.session_state["step"] = 1
            st.session_state["has_results"] = False

        st.button("Reset", on_click=reset)

    with col2:
        def go_next():
            st.session_state["step"] = 2

        st.button("Next ➜ Results", on_click=go_next)


# ============================================================
# STEP 2 — RESULTS
# ============================================================

elif step == 2:

    answers = get_answers(questions)

    if st.button("🚀 Calculate My D-Type"):

        st.session_state["has_results"] = True
        final_scores = normalize_scores(answers)

        primary_name, archetype_data = determine_archetype(final_scores, archetypes)
        probs, stability, shadow = monte_carlo_probabilities(final_scores, archetypes)

        shadow_name, shadow_pct = shadow

        # --------------------------------------------------------
        # RESULT CARD
        # --------------------------------------------------------

        st.markdown(f"""
        <div class="itype-result-card">
        <h1>{primary_name}</h1>
        <p>{archetype_data.get("description","")}</p>
        <p><b>Stability:</b> {stability:.1f}%</p>
        <p><b>Shadow:</b> {shadow_name} ({shadow_pct:.1f}%)</p>
        </div>
        """, unsafe_allow_html=True)

        # --------------------------------------------------------
        # RADAR CHART — MAP 0–1 → 0–100 VISUALLY
        # --------------------------------------------------------

        dims = CORE_DIMENSIONS
        vals = [final_scores[d] * 100 for d in dims]

        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=dims + [dims[0]],
            fill='toself',
            fillcolor='rgba(0,234,255,0.25)',
            line_color='#00eaff',
            line_width=3
        ))

        radar.update_layout(
            polar=dict(radialaxis=dict(range=[0, 100])),
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)'
        )

        st.plotly_chart(radar, use_container_width=True)

        # --------------------------------------------------------
        # D-TYPE HEATMAP (3×3 CLINICAL GRID)
        # --------------------------------------------------------

        heat_archetypes = [
            ["Analyst", "Detective", "Protocol Purist"],
            ["Stabiliser", "Harmoniser", "Lone Wolf"],
            ["Rapid Responder", "Situational Leader", "Innovator Clinician"]
        ]

        heat_values = [[probs.get(a, 0) for a in row] for row in heat_archetypes]

        heat = go.Figure(data=go.Heatmap(
            z=heat_values,
            x=["A1", "A2", "A3"],
            y=["B1", "B2", "B3"],
            colorscale="blues",
            showscale=True,
            hoverinfo="skip"
        ))

        annotations = []
        for i, row in enumerate(heat_archetypes):
            for j, a in enumerate(row):
                pct = probs.get(a, 0)
                annotations.append(dict(
                    x=j,
                    y=i,
                    text=f"<b>{a}</b><br>{pct:.1f}%",
                    showarrow=False,
                    font=dict(color="black", size=12)
                ))

        heat.update_layout(
            annotations=annotations,
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(heat, use_container_width=True)

        # --------------------------------------------------------
        # STRENGTHS / BLINDSPOTS
        # --------------------------------------------------------

        st.subheader("Strengths")
        for s in archetype_data.get("strengths", []):
            st.write(f"- {s}")

        st.subheader("Blindspots")
        for r in archetype_data.get("blindspots", []):
            st.write(f"- {r}")

    # Navigation buttons
    col1, col2 = st.columns(2)

    with col1:
        st.button("⬅ Back", on_click=lambda: st.session_state.update({"step": 1}))

    with col2:
        st.button("🔄 Start Over", on_click=lambda: st.session_state.update({"step": 1, "answers": {}, "has_results": False}))


# ============================================================
# ARCHETYPE EXPLORER
# ============================================================

if st.session_state.get("has_results"):
    st.markdown("## Explore All Archetypes")
    cols = st.columns(3)

    for idx, name in enumerate(archetypes.keys()):
        with cols[idx % 3]:
            if st.button(name, key=f"btn_{name}"):
                st.session_state["open_archetype"] = (
                    None if st.session_state["open_archetype"] == name else name
                )

    selected = st.session_state["open_archetype"]
    if selected:
        info = archetypes[selected]
        st.markdown(f"### {selected}")
        st.write(info.get("description", ""))

        st.subheader("Strengths")
        for s in info.get("strengths", []):
            st.write(f"- {s}")

        st.subheader("Blindspots")
        for b in info.get("blindspots", []):
            st.write(f"- {b}")
