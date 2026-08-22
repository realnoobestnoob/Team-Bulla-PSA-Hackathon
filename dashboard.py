"""
Green Port Control Tower — Streamlit Dashboard
Run: streamlit run dashboard.py  (from the project root)
"""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import plotly.graph_objects as go

# ── Project imports ───────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from loader import load_port_state
from agents.control_tower import run_control_tower
from agents import base as agent_base
from validator import validate_all
from impact import compute_baseline, compute_projected
from executor import execute_actions
from metrics import compute_run_score

# ── Constants ─────────────────────────────────────────────────────────────────
MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-3.6-flash",        # keep original default available
]
SCENARIOS = {
    "heavy_rain": "🌧 Heavy Rain + Equipment Shortage",
    "normal":     "☀️ Normal Operations",
}
PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
RISK_ICON     = {"high": "🔴", "medium": "🟡", "low": "🟢", "critical": "🚨"}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Green Port Control Tower",
    page_icon="🏗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session-state initialisation ──────────────────────────────────────────────
_DEFAULTS = {
    "phase":             "idle",   # idle | approval | complete
    "port_state":        None,
    "validated_actions": [],
    "baseline":          {},
    "projected":         {},
    "executed_actions":  [],
    "replan_count":      0,
    "replan_reason":     "",
    "run_metrics":       {},
    "token_usage":       {},
    "agent_log":         [],
    "show_replan":       False,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Core workflow helpers ─────────────────────────────────────────────────────

def do_planning(scenario: str, model: str, replan_reason: str = "") -> None:
    """Run AI agent + validation + impact; set phase → approval."""
    agent_base.set_model(model)
    log: list[str] = []

    port_state = load_port_state(scenario)
    st.session_state.port_state = port_state

    proposed  = run_control_tower(port_state, replan_reason=replan_reason, on_step=log.append)
    validated = validate_all(proposed, port_state)
    baseline  = compute_baseline(port_state)
    projected = compute_projected(validated, port_state)

    st.session_state.validated_actions = validated
    st.session_state.baseline          = baseline
    st.session_state.projected         = projected
    st.session_state.agent_log         = log
    st.session_state.show_replan       = False
    st.session_state.phase             = "approval"


def do_execution() -> None:
    """Execute approved actions; compute final KPIs; set phase → complete."""
    valid_actions = [a for a in st.session_state.validated_actions if a.get("valid", True)]
    new_state, executed, _ = execute_actions(valid_actions, st.session_state.port_state)

    token_usage = agent_base.get_last_token_usage()
    run_metrics = compute_run_score(
        baseline          = st.session_state.baseline,
        projected         = st.session_state.projected,
        validated_actions = st.session_state.validated_actions,
        executed_actions  = executed,
        replan_count      = st.session_state.replan_count,
        token_usage       = token_usage,
    )

    st.session_state.port_state       = new_state
    st.session_state.executed_actions = executed
    st.session_state.run_metrics      = run_metrics
    st.session_state.token_usage      = token_usage
    st.session_state.phase            = "complete"


def reset_run() -> None:
    for k in ["phase", "validated_actions", "baseline", "projected",
              "executed_actions", "agent_log", "run_metrics", "token_usage",
              "replan_count", "replan_reason", "show_replan"]:
        st.session_state[k] = _DEFAULTS.get(k, [] if "action" in k else {})


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏗 Control Tower")
    st.caption("PSA Code Sprint 2.0")
    st.divider()

    model    = st.selectbox("🤖 AI Model", MODELS)
    scenario = st.selectbox("📋 Scenario", list(SCENARIOS.keys()),
                            format_func=lambda k: SCENARIOS[k])
    st.divider()

    phase = st.session_state.phase

    if phase in ("idle", "complete"):
        if phase == "complete":
            st.success("✅ Run complete")
        if st.button("▶ Run Agent", type="primary", use_container_width=True):
            reset_run()
            with st.spinner("AI is planning…"):
                do_planning(scenario, model)
            st.rerun()

    elif phase == "approval":
        st.info("📋 Plan ready — review then decide")

        if st.button("✅ Approve & Execute", type="primary", use_container_width=True):
            with st.spinner("Executing actions…"):
                do_execution()
            st.rerun()

        if st.button("↺ Request Replan", use_container_width=True):
            st.session_state.show_replan = not st.session_state.show_replan

        if st.session_state.show_replan:
            reason = st.text_area("Constraint for replanning:",
                                  placeholder="e.g. prioritise J04, avoid V02",
                                  height=70)
            if st.button("Submit Replan", type="secondary") and reason:
                st.session_state.replan_count  += 1
                st.session_state.replan_reason  = reason
                with st.spinner(f"Replanning #{st.session_state.replan_count}…"):
                    do_planning(scenario, model, replan_reason=reason)
                st.rerun()

        st.divider()
        if st.button("❌ Cancel", use_container_width=True):
            reset_run()
            st.rerun()

    st.divider()
    status_label = {"idle": "⚪ Ready", "approval": "🟠 Awaiting approval",
                    "complete": "🟢 Complete"}.get(phase, "⚪")
    st.caption(f"Status: {status_label}")
    if st.session_state.replan_count:
        st.caption(f"Replans: {st.session_state.replan_count}")

    # API key warning
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("GOOGLE_API_KEY not set in .env")


# ── Main area ─────────────────────────────────────────────────────────────────
st.title("🏗 Green Port Control Tower")
st.caption("PSA Code Sprint 2.0 · AI-Driven Sustainability Orchestration")

tab_port, tab_plan, tab_perf = st.tabs(["📊 Port Status", "📋 Plan & Approve", "🎯 Performance"])


# ─── TAB 1 · Port Status ─────────────────────────────────────────────────────
with tab_port:
    port = st.session_state.port_state
    if port is None:
        st.info("▶ Click **Run Agent** in the sidebar to load the port state.")
    else:
        vehicles = port["vehicles"]
        jobs     = port["jobs"]
        weather  = port["weather"]
        energy   = port["energy"]

        # KPI strip
        ev       = [v for v in vehicles.values() if v["type"] == "electric"]
        dv       = [v for v in vehicles.values() if v["type"] == "diesel"]
        high_j   = [j for j in jobs.values() if j.get("priority") == "high"]
        grid_pct = round(energy["grid_load_kw"] / energy["grid_capacity_kw"] * 100)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("⚡ Electric Fleet",    len(ev),
                  f"avg {round(sum(v.get('battery',0) for v in ev)/max(len(ev),1))}% battery")
        c2.metric("🚛 Diesel Fleet",      len(dv),
                  f"avg {round(sum(v.get('fuel',0) for v in dv)/max(len(dv),1))}% fuel")
        c3.metric("🔴 High Priority Jobs", len(high_j), f"{len(jobs)} jobs total")
        c4.metric("⚡ Grid Load",          f"{grid_pct}%",
                  f"{energy['grid_load_kw']}/{energy['grid_capacity_kw']} kW")
        st.divider()

        col_fleet, col_jobs = st.columns(2)

        with col_fleet:
            st.subheader("🚛 Fleet")
            # Donut: status breakdown
            s_counts: dict = {}
            for v in vehicles.values():
                s = v.get("status", "unknown")
                s_counts[s] = s_counts.get(s, 0) + 1
            fig_pie = go.Figure(go.Pie(
                labels=list(s_counts.keys()), values=list(s_counts.values()),
                hole=0.55,
                marker_colors=["#22c55e","#3b82f6","#f59e0b","#ef4444","#a855f7"],
            ))
            fig_pie.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=180,
                                  legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig_pie, use_container_width=True)

            rows = []
            for vid, v in sorted(vehicles.items()):
                lvl = v.get("battery", v.get("fuel","?"))
                rows.append({"ID": vid,
                             "⚡/⛽": "⚡" if v["type"]=="electric" else "⛽",
                             "Loc": v.get("location","?"),
                             "Level": f"{lvl}%" if isinstance(lvl, int) else str(lvl),
                             "Status": v.get("status","?")})
            st.dataframe(rows, use_container_width=True, hide_index=True, height=200)

        with col_jobs:
            st.subheader("📦 Jobs")
            rows = []
            for jid, j in sorted(jobs.items()):
                rows.append({"ID": jid,
                             "P": PRIORITY_ICON.get(j.get("priority","low"),"⚪"),
                             "Route": f"{j['origin']}→{j['destination']}",
                             "Deadline": j.get("deadline","?"),
                             "Status": j.get("status","?")})
            st.dataframe(rows, use_container_width=True, hide_index=True, height=300)

        st.divider()
        col_wx, col_nrg = st.columns(2)

        with col_wx:
            st.subheader("🌤 Weather")
            cond = weather.get("condition","?").replace("_"," ").title()
            wind = weather.get("wind_speed", 0)
            rain = weather.get("rain_probability", 0)
            wa, wb = st.columns(2)
            wa.metric("Condition", cond)
            wb.metric("Wind", f"{wind} km/h",
                      delta="⚠ High" if isinstance(wind, (int,float)) and wind > 40 else None,
                      delta_color="inverse")
            if isinstance(rain, float):
                st.progress(rain, text=f"Rain probability: {round(rain*100)}%")

        with col_nrg:
            st.subheader("⚡ Energy")
            cap = energy["grid_capacity_kw"]
            fig_grid = go.Figure(go.Indicator(
                mode="gauge+number",
                value=energy["grid_load_kw"],
                number={"suffix": " kW"},
                gauge={
                    "axis": {"range": [0, cap]},
                    "bar":  {"color": "#3b82f6"},
                    "steps": [
                        {"range": [0, cap*0.7], "color": "#dcfce7"},
                        {"range": [cap*0.7, cap*0.9], "color": "#fef9c3"},
                        {"range": [cap*0.9, cap],      "color": "#fee2e2"},
                    ],
                    "threshold": {"line": {"color": "red","width":2}, "value": cap*0.9},
                },
            ))
            fig_grid.update_layout(height=200, margin=dict(t=20,b=0,l=20,r=20))
            st.plotly_chart(fig_grid, use_container_width=True)
            st.caption(f"Renewable fraction: {round(energy.get('renewable_fraction',0)*100)}%")


# ─── TAB 2 · Plan & Approve ──────────────────────────────────────────────────
with tab_plan:
    if st.session_state.phase == "idle":
        st.info("▶ Click **Run Agent** in the sidebar to generate a plan.")
    else:
        # Agent tool-call log
        if st.session_state.agent_log:
            with st.expander(f"🔧 Agent Tool Calls ({len(st.session_state.agent_log)} calls)", expanded=False):
                for entry in st.session_state.agent_log:
                    st.code(entry, language=None)

        # Action table
        actions = st.session_state.validated_actions
        if actions:
            st.subheader("📋 Proposed Actions")
            invalid = sum(1 for a in actions if not a.get("valid"))
            if invalid:
                st.warning(f"⚠ {invalid} action(s) failed validation and will be skipped.")

            rows = []
            for a in actions:
                p = a.get("parameters", {})
                rows.append({
                    "": "✅" if a.get("valid") else "❌",
                    "Type":    a.get("type","?"),
                    "Vehicle": p.get("vehicle_id","—"),
                    "Job":     p.get("job_id","—"),
                    "Risk":    f"{RISK_ICON.get(a.get('risk','low'),'⚪')} {a.get('risk','low')}",
                    "Reason":  (a.get("reason","")[:65] + "…") if len(a.get("reason","")) > 65 else a.get("reason",""),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

        # Impact comparison
        baseline  = st.session_state.baseline
        projected = st.session_state.projected
        if baseline and projected:
            st.subheader("📊 Impact vs All-Diesel Baseline")
            ci_col, cg_col = st.columns(2)

            with ci_col:
                fig_co2 = go.Figure()
                fig_co2.add_trace(go.Bar(name="Baseline (diesel)",
                    x=["Scenario"], y=[baseline.get("co2_kg",0)], marker_color="#ef4444"))
                fig_co2.add_trace(go.Bar(name="Proposed Plan",
                    x=["Scenario"], y=[projected.get("co2_kg",0)], marker_color="#22c55e"))
                fig_co2.add_trace(go.Bar(name="CO₂ Saved",
                    x=["Scenario"], y=[projected.get("co2_saved_kg",0)], marker_color="#3b82f6"))
                fig_co2.update_layout(title="CO₂ Emissions (kg)", barmode="group",
                                      height=280, margin=dict(t=40,b=0),
                                      legend=dict(orientation="h", y=-0.25))
                st.plotly_chart(fig_co2, use_container_width=True)

            with cg_col:
                proj_kw = projected.get("projected_grid_kw", 0)
                cap     = st.session_state.port_state["energy"]["grid_capacity_kw"]
                safe    = projected.get("grid_safe", True)
                fig_pg  = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=proj_kw,
                    title={"text": "Projected Grid Load (kW)"},
                    number={"suffix": " kW"},
                    gauge={
                        "axis": {"range": [0, cap]},
                        "bar":  {"color": "#22c55e" if safe else "#ef4444"},
                        "steps": [
                            {"range": [0, cap*0.7], "color": "#dcfce7"},
                            {"range": [cap*0.7, cap*0.9], "color": "#fef9c3"},
                            {"range": [cap*0.9, cap],      "color": "#fee2e2"},
                        ],
                    },
                ))
                fig_pg.update_layout(height=280, margin=dict(t=60,b=0,l=20,r=20))
                st.plotly_chart(fig_pg, use_container_width=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Jobs Covered",  projected.get("jobs_covered",0),
                      f"of {baseline.get('jobs_covered',0)} total")
            m2.metric("CO₂ Saved",     f"{projected.get('co2_saved_kg',0)} kg")
            m3.metric("Grid Status",   "✅ Safe" if projected.get("grid_safe") else "⚠ Overload")
            m4.metric("Delayed Jobs",  projected.get("delayed_jobs", 0))

        # Status banner
        if st.session_state.phase == "approval":
            st.divider()
            st.info("👤 **Supervisor action required** — use the buttons in the sidebar.")
        elif st.session_state.phase == "complete":
            st.success(f"✅ {len(st.session_state.executed_actions)} action(s) executed successfully.")


# ─── TAB 3 · Performance ─────────────────────────────────────────────────────
with tab_perf:
    metrics = st.session_state.run_metrics
    if not metrics:
        st.info("Performance score will appear after a run is approved and executed.")
    else:
        score    = metrics["total_score"]
        grade    = metrics["grade"]
        bd       = metrics["breakdown"]
        details  = metrics.get("details", {})
        tokens   = metrics.get("token_usage", {})
        t_eff    = metrics.get("token_efficiency", "—")

        g_colors = {"A+":"#22c55e","A":"#22c55e","B":"#84cc16",
                    "C":"#f59e0b","D":"#f97316","F":"#ef4444"}
        color = g_colors.get(grade, "#6b7280")

        sc_col, bd_col = st.columns([1, 2])

        with sc_col:
            fig_score = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                number={"suffix": "/100", "font": {"size": 36}},
                title={"text": f"<b>Grade: {grade}</b>", "font": {"size": 22}},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar":  {"color": color},
                    "steps": [
                        {"range": [0,  50], "color": "#fee2e2"},
                        {"range": [50, 70], "color": "#fef9c3"},
                        {"range": [70, 90], "color": "#dcfce7"},
                        {"range": [90,100], "color": "#bbf7d0"},
                    ],
                    "threshold": {"line": {"color":"black","width":2}, "value": 70},
                },
            ))
            fig_score.update_layout(height=300, margin=dict(t=60,b=0,l=20,r=20))
            st.plotly_chart(fig_score, use_container_width=True)

        with bd_col:
            st.subheader("Score Breakdown")
            cats   = list(bd.keys())
            vals   = list(bd.values())
            colors = ["#22c55e" if v >= 0 else "#ef4444" for v in vals]
            fig_bd = go.Figure(go.Bar(
                y=cats, x=vals, orientation="h",
                marker_color=colors,
                text=[f"{v:+.1f}" for v in vals],
                textposition="auto",
            ))
            fig_bd.update_layout(height=260, margin=dict(t=10,b=0,l=0,r=0),
                                 xaxis={"range":[-15, 45], "title":"Points"})
            st.plotly_chart(fig_bd, use_container_width=True)
            st.caption("Max: Emissions=40  Coverage=30  Grid=20  Quality=10 | Penalty −5/replan")

        st.divider()
        # Token usage row
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Prompt Tokens",     tokens.get("prompt_tokens","—"))
        t2.metric("Completion Tokens", tokens.get("completion_tokens","—"))
        t3.metric("Total Tokens",      tokens.get("total_tokens","—"))
        t4.metric("Token Efficiency",  t_eff)

        st.divider()
        # Run detail JSON cards
        d1, d2 = st.columns(2)
        with d1:
            st.subheader("Sustainability")
            st.json({"CO₂ saved (kg)":      details.get("co2_saved_kg", 0),
                     "Baseline CO₂ (kg)":   details.get("baseline_co2_kg", 0),
                     "Jobs dispatched":      details.get("jobs_dispatched", 0),
                     "Total actionable":     details.get("jobs_total", 0)})
        with d2:
            st.subheader("Operational")
            st.json({"Grid safe":        details.get("grid_safe", True),
                     "Valid actions":    details.get("valid_actions", 0),
                     "Total proposed":   details.get("total_proposed", 0),
                     "Replans needed":   details.get("replan_count", 0)})
