import streamlit as st
import json
import plotly.graph_objects as go

from idix_engine import (
    normalize_scores,
    determine_archetype,
    monte_carlo_probabilities,
)

# Optional anonymous logging
try:
    from data_logger_sheets import log_to_google_sheets as log_response

    HAS_LOGGER = True
except ImportError:
    HAS_LOGGER = False


# ============================================================
# SESSION STATE INITIALISATION
# ============================================================

if "step" not in st.session_state:
    st.session_state["step"] = 1  # 1 = Questions, 2 = Results

if "has_results" not in st.session_state:
    st.session_state["has_results"] = False

if "open_archetype" not in st.session_state:
    st.session_state["open_archetype"] = None

if "answers" not in st.session_state:  # persistent answers
    st.session_state["answers"] = {}


# ============================================================
# LOAD CSS
# ============================================================

def load_css():
    try:
        with open("assets/styles.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("⚠ Missing CSS file: assets/styles.css")


load_css()


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path, default=None):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default


questions = load_json("data/questions.json", default=[])
archetypes = load_json("data/archetypes.json", default={})


# ============================================================
# HERO SECTION
# ============================================================

st.markdown("""
<div class="hero-wrapper">
<div class="hero">
<div class="hero-glow"></div>
<div class="hero-particles"></div>
<div class="hero-content">
<h1 class="hero-title">I-TYPE — Innovator Type Assessment</h1>
<p class="hero-sub">Powered by the Innovator DNA Index™</p>
</div>
</div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# STEP PROGRESS BAR
# ============================================================

step = st.session_state["step"]
step_labels = {
    1: "Step 1 of 2 — Innovation Profile Questionnaire",
    2: "Step 2 of 2 — Your Innovator Type & Results",
}

st.markdown(f"### {step_labels[step]}")
st.progress(step / 2)


# ============================================================
# BUILD ANSWERS FROM SESSION STATE
# ============================================================

def get_answers_from_state(questions_list):
    answers = {}
    for i, q in enumerate(questions_list):
        key = f"q{i}"
        val = st.session_state["answers"].get(key, 3)

        answers[q["question"]] = {
            "value": val,
            "dimension": q.get("dimension", "thinking"),
            "reverse": q.get("reverse", False),
        }

    return answers


# ============================================================
# LIKERT LEGEND
# ============================================================

LIKERT_LEGEND = """
<div class="likert-legend">
<span>1 = Strongly Disagree</span>
<span>2 = Disagree</span>
<span>3 = Neutral</span>
<span>4 = Agree</span>
<span>5 = Strongly Agree</span>
</div>
"""


# ============================================================
# STEP 1 — QUESTIONS
# ============================================================

if step == 1:

    if not questions:
        st.error("❌ No questions found. Please check data/questions.json.")
    else:
        st.markdown(LIKERT_LEGEND, unsafe_allow_html=True)

        for i, q in enumerate(questions):
            st.markdown(
                f"<div class='itype-question'><p><b>{q['question']}</b></p></div>",
                unsafe_allow_html=True,
            )

            value = st.slider(
                label="",
                min_value=1,
                max_value=5,
                value=st.session_state["answers"].get(f"q{i}", 3),
                key=f"q{i}",
            )

            st.session_state["answers"][f"q{i}"] = value
            st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Reset"):
            for key in list(st.session_state.keys()):
                if key.startswith("q"):
                    del st.session_state[key]

            st.session_state["answers"] = {}
            st.session_state["step"] = 1
            st.session_state["has_results"] = False
            st.rerun()

    with col2:
        if st.button("Next ➜ See My Results"):
            st.session_state["step"] = 2
            st.rerun()


# ============================================================
# STEP 2 — RESULTS
# ============================================================

elif step == 2:

    if not questions or not archetypes:
        st.error("❌ Missing questions or archetypes.")
    else:
        answers = get_answers_from_state(questions)

        consent = st.checkbox(
            "I agree to anonymous numeric score logging (optional).",
            value=True
        )

        if consent:
            st.info("Your answers will be logged anonymously (numeric only).")

        if st.button("🚀 Calculate My Innovator Type"):

            st.session_state["has_results"] = True
            st.session_state["open_archetype"] = None

            final_scores = normalize_scores(answers)
            primary_name, archetype_data = determine_archetype(final_scores, archetypes)

            probs, stability, shadow = monte_carlo_probabilities(
                final_scores,
                archetypes
            )

            shadow_name, shadow_pct = shadow

            if HAS_LOGGER and consent:
                try:
                    log_response(
                        final_archetype=primary_name,
                        stability=stability,
                        shadow=shadow,
                        scores=final_scores,
                        raw_answers=answers
                    )
                except:
                    pass

            # ----------------------------
            # RESULT CARD
            # ----------------------------
            img_path = f"data/archetype_images/{primary_name}.png"
            try:
                st.image(img_path, use_column_width=False)
            except:
                pass

            st.markdown(f"""
            <div class="itype-result-card">
              <h1>{primary_name}</h1>
              <p>{archetype_data.get("description", "")}</p>
              <p><b>Stability:</b> {stability:.1f}%</p>
              <p><b>Shadow archetype:</b> {shadow_name} ({shadow_pct:.1f}%)</p>
            </div>
            """, unsafe_allow_html=True)

            # ----------------------------
            # RADAR CHART
            # ----------------------------
            dims = ["thinking", "execution", "risk", "motivation", "team", "commercial"]
            vals = [final_scores[d] for d in dims]

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
                polar=dict(
                    radialaxis=dict(range=[0, 100], visible=True),
                ),
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
            )

            st.plotly_chart(radar, use_container_width=True)

            # ----------------------------
            # PROBABILITY BAR PLOT
            # ----------------------------
            sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)

            bar = go.Figure()
            bar.add_trace(go.Bar(
                x=[p[0] for p in sorted_probs],
                y=[p[1] for p in sorted_probs],
                marker_color="#00eaff"
            ))

            st.plotly_chart(bar, use_container_width=True)

            # ----------------------------
            # ----------------------------
            # HEATMAP (with annotations)
            # ----------------------------
            heat_archetypes = [
                ["Visionary", "Strategist", "Storyteller"],
                ["Catalyst", "Apex Innovator", "Integrator"],
                ["Engineer", "Operator", "Experimenter"]
            ]
            
            heat_values = [
                [probs.get(a, 0) for a in row]
                for row in heat_archetypes
            ]
            
            row_labels = ["Ideation Cluster", "Activation Cluster", "Execution Cluster"]
            col_labels = ["Visionary", "Strategist", "Storyteller"]
            
            heat = go.Figure(data=go.Heatmap(
                z=heat_values,
                x=col_labels,
                y=row_labels,
                colorscale="blues",
                showscale=True,
                zmin=0,
                zmax=max(max(row) for row in heat_values) or 1,
                hoverinfo="skip"
            ))
            
            # Add text annotations for each cell
            annotations = []
            for i, row in enumerate(heat_archetypes):
                for j, archetype in enumerate(row):
                    pct = probs.get(archetype, 0)
                    annotations.append(dict(
                        x=col_labels[j],
                        y=row_labels[i],
                        text=f"<b>{archetype}</b><br>{pct:.1f}%",
                        showarrow=False,
                        font=dict(color="black", size=13),
                        align="center"
                    ))
            
            heat.update_layout(
                annotations=annotations,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=40, t=60, b=40),
                xaxis=dict(side="top")
            )
            
            st.plotly_chart(heat, use_container_width=True)
    

            # ----------------------------
            # TEXT BREAKDOWN
            # ----------------------------
            st.markdown("<hr><h2>Your Innovator Breakdown</h2>", unsafe_allow_html=True)

            st.subheader("Strengths")
            for s in archetype_data.get("strengths", []):
                st.markdown(f"- {s}")

            st.subheader("Growth Edges & Risks")
            for r in archetype_data.get("risks", []):
                st.markdown(f"- {r}")

            st.subheader("Recommended Innovation Pathways")
            for pth in archetype_data.get("pathways", []):
                st.markdown(f"- {pth}")

            st.subheader("Suggested Business Models")
            for bm in archetype_data.get("business_models", []):
                st.markdown(f"- {bm}")

            st.subheader("Funding Strategy Fit")
            for fs in archetype_data.get("funding_strategy", []):
                st.markdown(f"- {fs}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("⬅ Back to Questions"):
            st.session_state["step"] = 1
            st.session_state["has_results"] = False
            st.rerun()

    with col2:
        if st.button("🔄 Start Over"):
            st.session_state["answers"] = {}
            st.session_state["step"] = 1
            st.session_state["has_results"] = False
            st.rerun()


# ============================================================
# ARCHETYPE EXPLORER
# ============================================================

if st.session_state.get("has_results"):

    st.markdown("<hr class='hr-neon'>", unsafe_allow_html=True)
    st.markdown("## Explore All Archetypes")

    cols = st.columns(3)
    names = list(archetypes.keys())

    for idx, name in enumerate(names):
        with cols[idx % 3]:
            if st.button(name, key=f"btn_{name}", use_container_width=True):
                st.session_state["open_archetype"] = (
                    None if st.session_state["open_archetype"] == name else name
                )

    selected = st.session_state["open_archetype"]

    if selected:
        info = archetypes[selected]

        img_path = f"data/archetype_images/{selected}.png"
        try:
            st.image(img_path, use_column_width=True)
        except:
            pass

        st.markdown(f"### {selected}")
        st.write(info.get("description", ""))

        st.subheader("Strengths")
        for s in info.get("strengths", []):
            st.write(f"- {s}")

        st.subheader("Risks")
        for r in info.get("risks", []):
            st.write(f"- {r}")

        st.subheader("Pathways")
        for p in info.get("pathways", []):
            st.write(f"- {p}")

        st.subheader("Business Models")
        for b in info.get("business_models", []):
            st.write(f"- {b}")

        st.subheader("Funding Strategy Fit")
        for f in info.get("funding_strategy", []):
            st.write(f"- {f}")

