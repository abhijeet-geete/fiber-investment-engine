import csv
import io
from collections import Counter

import pandas as pd
import streamlit as st

import main


st.set_page_config(page_title="Fiber Investment Decision Engine", layout="wide")


PLAN_DESCRIPTIONS = {
    "Fiber 100": "Best for smaller households with light internet needs such as browsing, email, and a few connected devices.",
    "Fiber 300": "Good fit for medium households with several devices, streaming, video calls, and regular daily usage.",
    "Fiber Gig": "Strong choice for larger households, heavy streaming, work-from-home setups, gaming, and many active devices.",
    "2 Gig Fiber": "Premium option for very high-demand homes with many users, advanced gaming, creator workloads, and high device density.",
}


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


def recommendation_badge(label: str) -> str:
    if label == "APPROVE":
        return "🟢 APPROVE"
    if label == "REVIEW":
        return "🟡 REVIEW"
    return "🔴 DECLINE"


def confidence_badge(label: str) -> str:
    if label == "High":
        return "🟢 High"
    if label == "Medium":
        return "🟡 Medium"
    return "🔴 Low"


def render_single_result(result: dict) -> None:
    customer = result["customer"]

    st.subheader("Decision Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recommendation", recommendation_badge(result["recommendation"]))
    c2.metric("Confidence", confidence_badge(result["confidence"]))
    c3.metric("Final Score", result["final_score"])
    c4.metric("Break-even (months)", f"{result['break_even_months']:.1f}")

    left, right = st.columns([1, 1])

    with left:
        st.markdown("### Recommended Plan")
        st.success(
            f"""**{customer.recommended_plan_name}**

**Speed:** {customer.recommended_plan_speed_mbps} Mbps  
**Monthly Value:** ${customer.monthly_plan_value:.2f}  
**Installation Cost:** ${customer.installation_cost:.2f}  
**Installation Cost Tier:** {customer.installation_cost_tier}"""
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

    st.markdown("### Plan Evaluation")
    plan_rows = []
    for item in result["evaluated_plans"]:
        plan_rows.append({
            "Plan": item["plan"]["name"],
            "Base Score": item["base_score"],
            "Demand Adj": item["demand_score"],
            "Final Score": item["score"],
            "Decision": recommendation_badge(item["recommendation"]),
            "Break-even Months": round(item["break_even_months"], 1),
            "Demand Fit": item["demand_reason"],
        })
    st.dataframe(pd.DataFrame(plan_rows), use_container_width=True)

    st.markdown("### Decision Drivers")
    _, risk_reasons = main.evaluate_risk(customer)
    for item in risk_reasons:
        st.write(f"- {item}")

    st.markdown("### Confidence Drivers")
    _, confidence_reasons = main.calculate_confidence(customer)
    for item in confidence_reasons:
        st.write(f"- {item}")


def render_reasoning_tab() -> None:
    st.subheader("How the engine makes a decision")
    st.markdown(
        """
This tool follows a simple step-by-step process so the result is explainable, not a black box.

### 1. It gathers the customer profile
The engine first looks at the customer basics:
- homeowner or renter
- new or existing resident
- household size
- number of active devices
- current provider and whether they are unhappy
- credit score
- state

This tells the engine **who the customer is**, **how likely they are to switch**, and **what kind of internet demand they may have**.

### 2. It estimates installation cost
Instead of asking for a manual install cost, the engine assigns a **low, medium, or high install-cost tier** based on state.
That gives a rough real-world estimate of the upfront capital needed to install fiber.

### 3. It tests all available plans
The engine evaluates all four available plans one by one:
- Fiber 100
- Fiber 300
- Fiber Gig
- 2 Gig Fiber

For each plan, it checks both:
- the financial case
- the demand fit for that household

### 4. It calculates break-even
For each plan, it calculates:

**Break-even months = installation cost ÷ monthly plan value**

This tells us how long it would take to recover the upfront install investment.

### 5. It scores risk
The engine then adds a base risk score using signals like:
- likely switching intent
- credit profile
- expected retention
- whether the customer may move or sell before break-even

This answers:
**“Is this investment likely to make business sense?”**

### 6. It adjusts for household demand
Then it checks whether the plan fits the household’s usage:
- smaller households with fewer devices need less speed
- larger households with many devices need more speed

This creates a **demand-fit adjustment** so the engine does not only optimize for cost, but also for customer need.

### 7. It decides the best plan
After evaluating all four plans, the engine picks:
- the lowest-cost approved plan, if available
- otherwise the lowest-cost reviewable plan
- otherwise the highest-scoring fallback option

This keeps recommendations practical instead of always jumping to the most expensive plan.

### 8. It adds confidence
Confidence is separate from the investment recommendation.

- **Recommendation** answers: “Should we do this?”
- **Confidence** answers: “How sure are we?”

Confidence is influenced by things like:
- homeowner vs renter
- new vs existing resident
- lease length
- likely renewal
- whether a home sale is expected soon

### 9. It explains how to improve the case
If the result is not ideal, the engine also tells you what could improve it, such as:
- better credit profile
- longer expected tenure
- lower install cost
- shorter break-even
- stronger switching motivation

That makes the output more actionable for both internal teams and customer-facing conversations.
"""
    )


def render_available_plans_tab() -> None:
    st.subheader("Available Plans")
    st.caption("A simple side-by-side view to explain the differences to customers.")

    cols = st.columns(4)
    plans = main.PLANS

    for col, plan in zip(cols, plans):
        with col:
            speed = plan["speed_mbps"]
            if speed <= 100:
                fit = "Light usage"
                users = "1-2 users"
                devices = "Up to ~5 devices"
            elif speed <= 300:
                fit = "Moderate usage"
                users = "2-4 users"
                devices = "Up to ~10 devices"
            elif speed <= 1000:
                fit = "Heavy household usage"
                users = "4-6 users"
                devices = "10+ devices"
            else:
                fit = "Very high-demand usage"
                users = "Large / advanced households"
                devices = "Many active devices"

            st.markdown(
                f"""
### {plan["name"]}
**Speed:** {plan["speed_mbps"]} Mbps  
**Modeled Monthly Value:** ${plan["monthly_price"]:.2f}

**Best For:** {fit}  
**Typical Household:** {users}  
**Devices:** {devices}

{PLAN_DESCRIPTIONS.get(plan["name"], "")}
"""
            )

            if plan["name"] == "Fiber 100":
                st.info("Entry plan")
            elif plan["name"] == "Fiber 300":
                st.success("Balanced value")
            elif plan["name"] == "Fiber Gig":
                st.warning("Popular performance option")
            else:
                st.error("Premium top tier")

    st.markdown("### Plain-English difference")
    st.write("- **Fiber 100** is the basic option for lighter use.")
    st.write("- **Fiber 300** is a balanced middle option for most everyday households.")
    st.write("- **Fiber Gig** is better for larger or heavier-use homes.")
    st.write("- **2 Gig Fiber** is the premium option when speed demand is very high.")


st.title("Fiber Investment Decision Engine")
st.caption("AI-assisted decisioning for fiber deployment, with recommendation logic, confidence scoring, and portfolio analytics.")

tab0, tab1, tab2, tab3 = st.tabs([
    "🧠 Decision Reasoning Logic",
    "🎯 Individual Decision",
    "📊 Portfolio Analysis",
    "📶 Available Plans",
])

with tab0:
    render_reasoning_tab()

with tab1:
    st.subheader("Evaluate One Customer")
    with st.form("single_customer_form"):
        col1, col2 = st.columns(2)

        with col1:
            customer_name = st.text_input("Customer name", value="John")
            customer_type = st.selectbox("Customer type", ["homeowner", "renter"])
            resident_status = st.selectbox("Resident status", ["existing", "new"])
            household_size = st.number_input("Number of people in household", min_value=1, value=3, step=1)
            device_count = st.number_input("Number of active devices", min_value=1, value=8, step=1)
            current_provider = st.text_input("Current provider", value="comcast")
            is_unhappy = st.selectbox("Unhappy with current provider", ["yes", "no"])

        with col2:
            state = st.selectbox("State", sorted([
                "CA", "NY", "NJ", "WA", "MA", "TX", "FL", "IL", "CO", "GA", "KS", "OK", "AR", "MO", "IA"
            ]))
            credit_score = st.number_input("Credit score", min_value=300, max_value=850, value=720, step=1)

            if customer_type == "homeowner":
                planning_to_sell = st.selectbox("Planning to sell soon", ["no", "yes"])
                months_until_sale = st.number_input("Months until sale", min_value=0, value=0, step=1, disabled=(planning_to_sell == "no"))
                lease_months_remaining = 0
                likely_to_renew = "n/a"
            else:
                planning_to_sell = "n/a"
                months_until_sale = 0
                lease_months_remaining = st.number_input("Lease months remaining", min_value=0, value=12, step=1)
                likely_to_renew = st.selectbox("Likely to renew", ["yes", "no"])

        submitted = st.form_submit_button("Evaluate Customer", type="primary")

    if submitted:
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

with tab2:
    st.subheader("Portfolio Evaluation from CSV")
    st.markdown(
        "Required columns: `customer_name, customer_type, resident_status, state, credit_score, "
        "household_size, device_count, current_provider, is_unhappy`"
    )
    st.markdown(
        "Optional columns: `planning_to_sell, months_until_sale, lease_months_remaining, likely_to_renew`"
    )

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            results = load_results_from_uploaded_csv(uploaded_file)
            df = results_to_dataframe(results)
            summary = compute_portfolio_summary(results)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Customers", summary["total_customers"])
            c2.metric("Approves", summary["approves"])
            c3.metric("Reviews", summary["reviews"])
            c4.metric("Declines", summary["declines"])

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Avg Break-even", f"{summary['avg_break_even']:.1f} mo")
            c6.metric("Avg Score", f"{summary['avg_final_score']:.1f}")
            c7.metric("Avg Install Cost", f"${summary['avg_install_cost']:,.0f}")
            c8.metric("Top Plan", summary["top_plan"])

            st.markdown("### Confidence Mix")
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("🟢 High", summary["high_confidence"])
            cc2.metric("🟡 Medium", summary["medium_confidence"])
            cc3.metric("🔴 Low", summary["low_confidence"])

            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
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
                st.markdown("### Plan Distribution")
                plan_chart_df = pd.DataFrame({
                    "Plan": list(summary["plan_counts"].keys()),
                    "Count": list(summary["plan_counts"].values()),
                }).set_index("Plan")
                if not plan_chart_df.empty:
                    st.bar_chart(plan_chart_df)

            st.markdown("### Results")
            st.dataframe(df, use_container_width=True)

            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Results CSV",
                data=csv_bytes,
                file_name="portfolio_results.csv",
                mime="text/csv",
            )
        except Exception as e:
            st.error(f"Could not process CSV: {e}")

with tab3:
    render_available_plans_tab()
