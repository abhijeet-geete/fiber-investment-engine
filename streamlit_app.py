import csv
import io
import time
from collections import Counter

import pandas as pd
import streamlit as st

import main


st.set_page_config(page_title="Fiber Investment Decision Engine", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #f5f7fb 0%, #eef4ff 100%);
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    h1, h2, h3 {
        color: #14213d;
    }

    .subtitle {
        color: #4f5d75;
        margin-top: -0.5rem;
        margin-bottom: 1rem;
    }

    .card {
        background: white;
        padding: 1.25rem 1.25rem 1rem 1.25rem;
        border-radius: 16px;
        border: 1px solid #e6ebf2;
        box-shadow: 0 8px 24px rgba(20, 33, 61, 0.06);
        margin-bottom: 1rem;
    }

    .metric-tile {
        background: white;
        padding: 1rem;
        border-radius: 14px;
        border: 1px solid #e6ebf2;
        box-shadow: 0 6px 20px rgba(20, 33, 61, 0.05);
        text-align: center;
    }

    .pill {
        display: inline-block;
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.9rem;
        margin-right: 0.4rem;
    }

    .pill-green { background: #e8f7ee; color: #1b7f3a; }
    .pill-yellow { background: #fff6db; color: #9a6a00; }
    .pill-red { background: #fdecec; color: #b42318; }
    .pill-blue { background: #ebf3ff; color: #175cd3; }

    input, textarea, select {
        background-color: white !important;
    }

    div[data-baseweb="input"] input {
        background-color: white !important;
    }

    div[data-baseweb="select"] > div {
        background-color: white !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.05rem;
    }

    .small-note {
        color: #667085;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


PLAN_DESCRIPTIONS = {
    "Fiber 100": "Best for smaller households with light internet needs such as browsing, email, and a few connected devices.",
    "Fiber 300": "Good fit for medium households with several devices, streaming, video calls, and regular daily usage.",
    "Fiber Gig": "Strong choice for larger households, heavy streaming, work-from-home setups, gaming, and many active devices.",
    "2 Gig Fiber": "Premium option for very high-demand homes with many users, advanced gaming, creator workloads, and high device density.",
}


def recommendation_badge_html(label: str) -> str:
    if label == "APPROVE":
        return "<span class='pill pill-green'>🟢 APPROVE</span>"
    if label == "REVIEW":
        return "<span class='pill pill-yellow'>🟡 REVIEW</span>"
    return "<span class='pill pill-red'>🔴 DECLINE</span>"


def confidence_badge_html(label: str) -> str:
    if label == "High":
        return "<span class='pill pill-green'>🟢 High</span>"
    if label == "Medium":
        return "<span class='pill pill-yellow'>🟡 Medium</span>"
    return "<span class='pill pill-red'>🔴 Low</span>"


def result_to_row(result: dict) -> dict:
    customer = result["customer"]
    return {
        "customer_name": customer.customer_name,
        "customer_type": customer.customer_type,
        "resident_status": customer.resident_status,
        "state": customer.state,
        "household_size": customer.household_size,
        "device_count": customer.device_count,
        "current_provider": customer.current_provider,
        "credit_score": customer.credit_score,
        "recommended_plan_name": customer.recommended_plan_name,
        "recommended_plan_speed_mbps": customer.recommended_plan_speed_mbps,
        "monthly_plan_value": round(customer.monthly_plan_value, 2),
        "installation_cost": round(customer.installation_cost, 2),
        "installation_cost_tier": customer.installation_cost_tier,
        "break_even_months": round(result["break_even_months"], 1),
        "base_score": result["base_score"],
        "demand_score": result["demand_score"],
        "final_score": result["final_score"],
        "recommendation": result["recommendation"],
        "confidence": result["confidence"],
        "improvement_suggestions": " | ".join(result["improvement_suggestions"]),
    }


def results_to_dataframe(results: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([result_to_row(r) for r in results])


def compute_portfolio_summary(results: list[dict]) -> dict:
    recommendation_counts = Counter(r["recommendation"] for r in results)
    confidence_counts = Counter(r["confidence"] for r in results)
    plan_counts = Counter(r["customer"].recommended_plan_name for r in results)

    total_install_cost = sum(r["customer"].installation_cost for r in results)
    avg_install_cost = total_install_cost / len(results) if results else 0
    avg_break_even = sum(r["break_even_months"] for r in results) / len(results) if results else 0
    avg_final_score = sum(r["final_score"] for r in results) / len(results) if results else 0

    return {
        "total_customers": len(results),
        "approves": recommendation_counts.get("APPROVE", 0),
        "reviews": recommendation_counts.get("REVIEW", 0),
        "declines": recommendation_counts.get("DECLINE", 0),
        "high_confidence": confidence_counts.get("High", 0),
        "medium_confidence": confidence_counts.get("Medium", 0),
        "low_confidence": confidence_counts.get("Low", 0),
        "top_plan": plan_counts.most_common(1)[0][0] if plan_counts else "N/A",
        "total_install_cost": total_install_cost,
        "avg_install_cost": avg_install_cost,
        "avg_break_even": avg_break_even,
        "avg_final_score": avg_final_score,
        "recommendation_counts": recommendation_counts,
        "plan_counts": plan_counts,
    }


def load_results_from_uploaded_csv(uploaded_file) -> list[dict]:
    text_stream = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
    reader = csv.DictReader(text_stream)

    required_columns = {
        "customer_name",
        "customer_type",
        "resident_status",
        "state",
        "credit_score",
        "household_size",
        "device_count",
        "current_provider",
        "is_unhappy",
    }

    missing = required_columns - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    results = []

    for row in reader:
        customer_type = row["customer_type"].strip().lower()
        customer_name = row["customer_name"].strip()
        resident_status = row["resident_status"].strip().lower()
        state = row["state"].strip().upper()
        credit_score = int(row["credit_score"])
        household_size = int(row["household_size"])
        device_count = int(row["device_count"])
        current_provider = row["current_provider"].strip().lower()
        is_unhappy = row["is_unhappy"].strip().lower()

        if customer_type == "homeowner":
            planning_to_sell = row.get("planning_to_sell", "no").strip().lower() or "no"
            months_until_sale = int(row.get("months_until_sale", 0) or 0)
            lease_months_remaining = 0
            likely_to_renew = "n/a"
        else:
            planning_to_sell = "n/a"
            months_until_sale = 0
            lease_months_remaining = int(row.get("lease_months_remaining", 12) or 12)
            likely_to_renew = row.get("likely_to_renew", "yes").strip().lower() or "yes"

        base_customer = main.create_base_customer_from_inputs(
            customer_name=customer_name,
            customer_type=customer_type,
            resident_status=resident_status,
            household_size=household_size,
            device_count=device_count,
            current_provider=current_provider,
            is_unhappy_with_current_provider=is_unhappy,
            planning_to_sell=planning_to_sell,
            months_until_sale=months_until_sale,
            lease_months_remaining=lease_months_remaining,
            likely_to_renew=likely_to_renew,
            credit_score=credit_score,
            state=state,
        )
        results.append(main.solve_customer(base_customer))

    return results


def render_header():
    st.markdown("<h1>🚀 Fiber Investment Decision Engine</h1>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>Decision workspace for fiber deployment planning, customer-fit scoring, and portfolio analysis.</div>",
        unsafe_allow_html=True,
    )


def render_metric_tile(title: str, value: str):
    st.markdown(
        f"""
        <div class="metric-tile">
            <div class="small-note">{title}</div>
            <div style="font-size:1.2rem;font-weight:700;color:#14213d;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_single_result(result: dict) -> None:
    customer = result["customer"]

    st.subheader("Decision Summary")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_tile("Recommendation", recommendation_badge_html(result["recommendation"]))
    with c2:
        render_metric_tile("Confidence", confidence_badge_html(result["confidence"]))
    with c3:
        render_metric_tile("Final Score", str(result["final_score"]))
    with c4:
        render_metric_tile("Break-even (months)", f"{result['break_even_months']:.1f}")

    left, right = st.columns([1.1, 1])

    with left:
        st.markdown("### Recommended Plan")
        st.markdown(
            f"""
            <div class="pill pill-blue">{customer.recommended_plan_name}</div>
            <div style="margin-top:0.8rem;">
            <strong>Speed:</strong> {customer.recommended_plan_speed_mbps} Mbps<br>
            <strong>Modeled Monthly Value:</strong> ${customer.monthly_plan_value:.2f}<br>
            <strong>Installation Cost:</strong> ${customer.installation_cost:.2f}<br>
            <strong>Installation Cost Tier:</strong> {customer.installation_cost_tier}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("### Why This Plan")
        for item in result["plan_justification"]:
            st.write(f"- {item}")

        st.markdown("### What Would Improve This Decision")
        for item in result["improvement_suggestions"]:
            st.write(f"- {item}")
        
    with right:
        st.markdown("### Customer Profile")
        st.write(f"**Customer:** {customer.customer_name}")
        st.write(f"**Type:** {customer.customer_type}")
        st.write(f"**Resident Status:** {customer.resident_status}")
        st.write(f"**State:** {customer.state}")
        st.write(f"**Household Size:** {customer.household_size}")
        st.write(f"**Active Devices:** {customer.device_count}")
        st.write(f"**Current Provider:** {customer.current_provider}")
        st.write(f"**Credit Score:** {customer.credit_score}")

        if customer.customer_type == "homeowner":
            st.write(f"**Planning to Sell Soon:** {customer.planning_to_sell}")
            if customer.planning_to_sell == "yes":
                st.write(f"**Months Until Sale:** {customer.months_until_sale}")
        else:
            st.write(f"**Lease Months Remaining:** {customer.lease_months_remaining}")
            st.write(f"**Likely to Renew:** {customer.likely_to_renew}")
        
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Plan Evaluation")
    plan_rows = []
    for item in result["evaluated_plans"]:
        plan_rows.append({
            "Plan": item["plan"]["name"],
            "Base Score": item["base_score"],
            "Demand Adj": item["demand_score"],
            "Final Score": item["score"],
            "Decision": item["recommendation"],
            "Break-even Months": round(item["break_even_months"], 1),
            "Demand Fit": item["demand_reason"],
        })
    st.dataframe(pd.DataFrame(plan_rows), width="stretch")
    
    drivers_left, drivers_right = st.columns(2)
    with drivers_left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### Decision Drivers")
        _, risk_reasons = main.evaluate_risk(customer)
        for item in risk_reasons:
            st.write(f"- {item}")
        
    with drivers_right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### Confidence Drivers")
        _, confidence_reasons = main.calculate_confidence(customer)
        for item in confidence_reasons:
            st.write(f"- {item}")
        

def render_reasoning_tab() -> None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("How the engine makes a decision")
    st.markdown(
        """
This tool follows a step-by-step decision process so the output is explainable.

### 1. Customer profile
The engine gathers core facts:
- homeowner or renter
- new or existing resident
- household size
- active devices
- current provider and switching intent
- credit score
- state

### 2. Installation cost estimate
The system assigns an install-cost tier based on state:
- **Low-cost tier:** $800
- **Medium-cost tier:** $1200
- **High-cost tier:** $1600

### 3. All plans are tested
Each case is evaluated across all four plan options:
- **Fiber 100** → modeled monthly value **$40**
- **Fiber 300** → modeled monthly value **$60**
- **Fiber Gig** → modeled monthly value **$80**
- **2 Gig Fiber** → modeled monthly value **$120**

### 4. Break-even is calculated
**Break-even months = installation cost ÷ monthly plan value**

This means break-even changes based on both:
- geography / install cost tier
- the plan’s monthly modeled value

### 5. Risk score is built
The engine scores:
- switching likelihood
- retention outlook
- break-even economics
- credit profile
- likely move/sale timing

### 6. Demand fit is added
A plan is adjusted up or down depending on:
- number of household users
- number of active devices

### 7. Best-fit plan is selected
The system chooses:
- the lowest-cost approved plan
- otherwise the lowest-cost reviewable plan
- otherwise the highest-scoring fallback

### 8. Confidence is separate
- **Recommendation** = should we do this?
- **Confidence** = how sure are we?

### 9. Improvement suggestions are added
If a case is weak, the system explains what would improve it:
- stronger credit
- longer tenure
- shorter break-even
- lower install cost
- better switching motivation
"""
    )
    

def render_available_plans_tab() -> None:
    st.subheader("Available Plans")
    st.caption("A side-by-side plan view for customer conversations and product comparison.")
    cols = st.columns(4)

    for col, plan in zip(cols, main.PLANS):
        with col:
            speed = plan["speed_mbps"]
            if speed <= 100:
                badge = "Entry plan"
                kind = "info"
                fit = "Light usage"
                users = "1-2 users"
                devices = "Up to ~5 devices"
            elif speed <= 300:
                badge = "Balanced value"
                kind = "success"
                fit = "Moderate usage"
                users = "2-4 users"
                devices = "Up to ~10 devices"
            elif speed <= 1000:
                badge = "Popular performance option"
                kind = "warning"
                fit = "Heavy household usage"
                users = "4-6 users"
                devices = "10+ devices"
            else:
                badge = "Premium top tier"
                kind = "error"
                fit = "Very high-demand usage"
                users = "Large / advanced households"
                devices = "Many active devices"

            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"### {plan['name']}")
            st.markdown(
                f"""
**Speed:** {plan["speed_mbps"]} Mbps  
**Modeled Monthly Value:** ${plan["monthly_price"]:.2f}

**Best For:** {fit}  
**Typical Household:** {users}  
**Devices:** {devices}

{PLAN_DESCRIPTIONS.get(plan["name"], "")}
"""
            )
            getattr(st, kind)(badge)
            
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Plain-English difference")
    st.write("- **Fiber 100** is the basic option for lighter use.")
    st.write("- **Fiber 300** is a balanced middle option for most everyday households.")
    st.write("- **Fiber Gig** is better for larger or heavier-use homes.")
    st.write("- **2 Gig Fiber** is the premium option when speed demand is very high.")
    

render_header()

tab_plans, tab_logic, tab_single, tab_bulk = st.tabs([
    "📶 Available Plans",
    "🧠 Decision Reasoning Logic",
    "🎯 Individual Decision",
    "📊 Bulk Analysis",
])

with tab_plans:
    render_available_plans_tab()

with tab_logic:
    render_reasoning_tab()

with tab_single:
    st.subheader("Evaluate One Customer")
    left, right = st.columns([1, 1])

    with left:
        customer_name = st.text_input("Customer name", value="")
        customer_type = st.selectbox("Customer type", ["homeowner", "renter"], index=0)
        resident_status = st.selectbox("Resident status", ["existing", "new"], index=0)
        household_size = st.number_input("Number of people in household", min_value=1, value=1, step=1)
        device_count = st.number_input("Number of active devices", min_value=1, value=1, step=1)
        current_provider = st.text_input("Current provider", value="")
        is_unhappy = st.selectbox("Unhappy with current provider", ["yes", "no"], index=0)
        
    with right:
        state_options = [""] + sorted([
            "CA", "NY", "NJ", "WA", "MA", "TX", "FL", "IL", "CO", "GA", "KS", "OK", "AR", "MO", "IA"
        ])
        state = st.selectbox("State", state_options, index=0)
        credit_score = st.number_input("Credit score", min_value=300, max_value=850, value=720, step=1)

        if customer_type == "homeowner":
            planning_to_sell = st.selectbox("Planning to sell soon", ["no", "yes"], index=0)
            months_until_sale = st.number_input(
                "Months until sale",
                min_value=0,
                value=0,
                step=1,
                disabled=(planning_to_sell != "yes"),
            )
            lease_months_remaining = 0
            likely_to_renew = "n/a"
        else:
            planning_to_sell = "n/a"
            months_until_sale = 0
            lease_months_remaining = st.number_input("Lease months remaining", min_value=0, value=12, step=1)
            likely_to_renew = st.selectbox("Likely to renew", ["yes", "no"], index=0)

        evaluate_clicked = st.button("Evaluate Customer", type="primary", width="stretch")
        
    if evaluate_clicked:
        if not customer_name.strip():
            st.error("Please enter customer name.")
        elif not state:
            st.error("Please select a state.")
        else:
            with st.spinner("Evaluating customer profile, economics, and best-fit plan..."):
                time.sleep(3)
                base_customer = main.create_base_customer_from_inputs(
                    customer_name=customer_name,
                    customer_type=customer_type,
                    resident_status=resident_status,
                    household_size=int(household_size),
                    device_count=int(device_count),
                    current_provider=current_provider.strip().lower() or "none",
                    is_unhappy_with_current_provider=is_unhappy,
                    planning_to_sell=planning_to_sell,
                    months_until_sale=int(months_until_sale),
                    lease_months_remaining=int(lease_months_remaining),
                    likely_to_renew=likely_to_renew,
                    credit_score=int(credit_score),
                    state=state,
                )
                result = main.solve_customer(base_customer)

            render_single_result(result)

with tab_bulk:
    st.subheader("Bulk Analysis")
    upload_col, info_col = st.columns([1, 1])

    with upload_col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### Upload CSV")
        st.markdown(
            "Required columns: `customer_name, customer_type, resident_status, state, credit_score, "
            "household_size, device_count, current_provider, is_unhappy`"
        )
        st.markdown(
            "Optional columns: `planning_to_sell, months_until_sale, lease_months_remaining, likely_to_renew`"
        )
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file is not None:
            st.success(f"File loaded: {uploaded_file.name}")
            evaluate_bulk = st.button("Evaluate Bulk File", type="primary", width="stretch")
        else:
            evaluate_bulk = False
        
    with info_col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### What happens here")
        st.write("- Upload a customer CSV")
        st.write("- The engine evaluates every row")
        st.write("- You get a recommendation mix, plan mix, and results table")
        st.write("- You can download the evaluated results as CSV")
        
    if uploaded_file is not None and evaluate_bulk:
        try:
            with st.spinner("Evaluating bulk file and preparing portfolio dashboard..."):
                time.sleep(2)
                results = load_results_from_uploaded_csv(uploaded_file)
                df = results_to_dataframe(results)
                summary = compute_portfolio_summary(results)

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                render_metric_tile("Customers", str(summary["total_customers"]))
            with m2:
                render_metric_tile("Approves", str(summary["approves"]))
            with m3:
                render_metric_tile("Reviews", str(summary["reviews"]))
            with m4:
                render_metric_tile("Declines", str(summary["declines"]))

            m5, m6, m7, m8 = st.columns(4)
            with m5:
                render_metric_tile("Avg Break-even", f"{summary['avg_break_even']:.1f} mo")
            with m6:
                render_metric_tile("Avg Score", f"{summary['avg_final_score']:.1f}")
            with m7:
                render_metric_tile("Avg Install Cost", f"${summary['avg_install_cost']:,.0f}")
            with m8:
                render_metric_tile("Top Plan", summary["top_plan"])

            conf1, conf2, conf3 = st.columns(3)
            with conf1:
                render_metric_tile("🟢 High Confidence", str(summary["high_confidence"]))
            with conf2:
                render_metric_tile("🟡 Medium Confidence", str(summary["medium_confidence"]))
            with conf3:
                render_metric_tile("🔴 Low Confidence", str(summary["low_confidence"]))

            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("### Recommendation Mix")
                rec_chart_df = pd.DataFrame({
                    "Recommendation": ["APPROVE", "REVIEW", "DECLINE"],
                    "Count": [
                        summary["recommendation_counts"].get("APPROVE", 0),
                        summary["recommendation_counts"].get("REVIEW", 0),
                        summary["recommendation_counts"].get("DECLINE", 0),
                    ],
                }).set_index("Recommendation")
                st.bar_chart(rec_chart_df)
                
            with chart_col2:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("### Plan Distribution")
                plan_chart_df = pd.DataFrame({
                    "Plan": list(summary["plan_counts"].keys()),
                    "Count": list(summary["plan_counts"].values()),
                }).set_index("Plan")
                if not plan_chart_df.empty:
                    st.bar_chart(plan_chart_df)
                
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("### Results Table")
            st.dataframe(df, width="stretch")

            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Results CSV",
                data=csv_bytes,
                file_name="portfolio_results.csv",
                mime="text/csv",
                width="stretch",
            )
            
        except Exception as e:
            st.error(f"Could not process CSV: {e}")
