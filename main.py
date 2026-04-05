from dataclasses import dataclass
from collections import Counter
from pathlib import Path
import csv
import math


PLANS = [
    {"name": "Fiber 100", "speed_mbps": 100, "monthly_price": 40},
    {"name": "Fiber 300", "speed_mbps": 300, "monthly_price": 60},
    {"name": "Fiber Gig", "speed_mbps": 1000, "monthly_price": 80},
    {"name": "2 Gig Fiber", "speed_mbps": 2000, "monthly_price": 120},
]

INSTALL_COST_TIERS = {
    "low": 800,
    "medium": 1200,
    "high": 1600,
}

STATE_COST_MAP = {
    "CA": "high",
    "NY": "high",
    "NJ": "high",
    "WA": "high",
    "MA": "high",
    "TX": "medium",
    "FL": "medium",
    "IL": "medium",
    "CO": "medium",
    "GA": "medium",
    "KS": "low",
    "OK": "low",
    "AR": "low",
    "MO": "low",
    "IA": "low",
}


@dataclass
class CustomerCase:
    customer_name: str
    customer_type: str
    resident_status: str
    current_provider: str
    is_unhappy_with_current_provider: str
    planning_to_sell: str
    months_until_sale: int
    lease_months_remaining: int
    likely_to_renew: str
    credit_score: int
    monthly_plan_value: float
    installation_cost: float
    state: str
    installation_cost_tier: str
    recommended_plan_name: str
    recommended_plan_speed_mbps: int
    household_size: int
    device_count: int


SAMPLE_CUSTOMERS = [
    {
        "customer_name": "Ava",
        "customer_type": "homeowner",
        "resident_status": "existing",
        "current_provider": "comcast",
        "is_unhappy_with_current_provider": "yes",
        "planning_to_sell": "no",
        "months_until_sale": 0,
        "lease_months_remaining": 0,
        "likely_to_renew": "n/a",
        "credit_score": 780,
        "state": "KS",
        "household_size": 2,
        "device_count": 4,
    },
    {
        "customer_name": "Ben",
        "customer_type": "renter",
        "resident_status": "new",
        "current_provider": "ziply",
        "is_unhappy_with_current_provider": "no",
        "planning_to_sell": "n/a",
        "months_until_sale": 0,
        "lease_months_remaining": 5,
        "likely_to_renew": "no",
        "credit_score": 620,
        "state": "CA",
        "household_size": 1,
        "device_count": 3,
    },
    {
        "customer_name": "Chloe",
        "customer_type": "homeowner",
        "resident_status": "existing",
        "current_provider": "none",
        "is_unhappy_with_current_provider": "no",
        "planning_to_sell": "yes",
        "months_until_sale": 18,
        "lease_months_remaining": 0,
        "likely_to_renew": "n/a",
        "credit_score": 710,
        "state": "TX",
        "household_size": 4,
        "device_count": 10,
    },
    {
        "customer_name": "Daniel",
        "customer_type": "renter",
        "resident_status": "existing",
        "current_provider": "comcast",
        "is_unhappy_with_current_provider": "yes",
        "planning_to_sell": "n/a",
        "months_until_sale": 0,
        "lease_months_remaining": 14,
        "likely_to_renew": "yes",
        "credit_score": 760,
        "state": "WA",
        "household_size": 5,
        "device_count": 14,
    },
    {
        "customer_name": "Ethan",
        "customer_type": "homeowner",
        "resident_status": "new",
        "current_provider": "att",
        "is_unhappy_with_current_provider": "yes",
        "planning_to_sell": "yes",
        "months_until_sale": 6,
        "lease_months_remaining": 0,
        "likely_to_renew": "n/a",
        "credit_score": 590,
        "state": "NY",
        "household_size": 3,
        "device_count": 8,
    },
]


def calculate_break_even_months(installation_cost: float, monthly_plan_value: float) -> float:
    if monthly_plan_value <= 0:
        return 0
    return installation_cost / monthly_plan_value


def calculate_confidence(customer: CustomerCase) -> tuple[str, list[str]]:
    confidence_score = 0
    reasons = []

    if customer.customer_type == "homeowner":
        confidence_score += 2
        reasons.append("Homeowner profile provides stronger location stability signal.")
    elif customer.customer_type == "renter":
        confidence_score += 1
        reasons.append("Renter profile has moderate predictability.")

    if customer.resident_status == "existing":
        confidence_score += 2
        reasons.append("Existing resident adds confidence because the household is more established.")
    elif customer.resident_status == "new":
        confidence_score += 1
        reasons.append("New resident adds some uncertainty because tenure is less proven.")

    if customer.customer_type == "homeowner":
        if customer.planning_to_sell == "no":
            confidence_score += 2
            reasons.append("No near-term home sale planned, which improves confidence.")
        elif customer.planning_to_sell == "yes":
            reasons.append("Planned home sale reduces certainty about long-term retention.")

    elif customer.customer_type == "renter":
        if customer.lease_months_remaining >= 12:
            confidence_score += 2
            reasons.append("Long remaining lease term improves confidence.")
        elif customer.lease_months_remaining >= 6:
            confidence_score += 1
            reasons.append("Moderate remaining lease term provides some confidence.")
        else:
            reasons.append("Short remaining lease term reduces confidence.")

        if customer.likely_to_renew == "yes":
            confidence_score += 1
            reasons.append("Likely renewal improves confidence.")
        elif customer.likely_to_renew == "no":
            reasons.append("No expected renewal lowers confidence in retention.")

    if confidence_score >= 6:
        return "High", reasons
    elif confidence_score >= 3:
        return "Medium", reasons
    return "Low", reasons


def evaluate_risk(customer: CustomerCase) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    if customer.customer_type.lower() == "homeowner":
        score += 2
        reasons.append("Homeowner is generally more stable.")
    elif customer.customer_type.lower() == "renter":
        reasons.append("Renter may have higher move-out risk.")

    if customer.current_provider != "none":
        reasons.append(f"Customer currently uses {customer.current_provider}.")
    else:
        reasons.append("Customer does not currently have an internet provider.")

    if customer.current_provider != "none" and customer.is_unhappy_with_current_provider == "yes":
        score += 2
        reasons.append("Customer is unhappy with current provider, which may improve switching likelihood.")
    elif customer.current_provider != "none" and customer.is_unhappy_with_current_provider == "no":
        score -= 1
        reasons.append("Customer appears satisfied with current provider, which may reduce switching likelihood.")

    break_even_months = calculate_break_even_months(
        customer.installation_cost, customer.monthly_plan_value
    )

    if break_even_months <= 6:
        score += 3
        reasons.append("Company can recover installation cost quickly.")
    elif break_even_months <= 12:
        score += 2
        reasons.append("Recovery period is acceptable.")
    else:
        reasons.append("Recovery period is long, which increases risk.")

    if customer.customer_type == "homeowner":
        if customer.planning_to_sell == "no":
            score += 2
            reasons.append("Homeowner is not planning to sell soon, improving recovery confidence.")
        elif customer.planning_to_sell == "yes":
            if customer.months_until_sale >= break_even_months:
                score += 1
                reasons.append("Expected sale timing still allows enough time to recover installation cost.")
            else:
                score -= 3
                reasons.append("Customer may sell the home before break-even, increasing capital loss risk.")

    elif customer.customer_type == "renter":
        if customer.lease_months_remaining >= break_even_months:
            score += 1
            reasons.append("Remaining lease term appears long enough to support cost recovery.")
        elif customer.lease_months_remaining < break_even_months and customer.likely_to_renew == "yes":
            reasons.append("Current lease ends before break-even, but likely renewal may reduce risk.")
        elif customer.lease_months_remaining < break_even_months and customer.likely_to_renew == "no":
            score -= 3
            reasons.append("Lease may end before break-even and renewal is unlikely, increasing loss risk.")

    if customer.credit_score >= 750:
        score += 3
        reasons.append("Strong credit score.")
    elif customer.credit_score >= 650:
        score += 2
        reasons.append("Moderate credit score.")
    elif customer.credit_score >= 550:
        score += 1
        reasons.append("Below-average credit score.")
    else:
        reasons.append("Weak credit score.")

    return score, reasons


def get_recommendation(score: int) -> str:
    if score >= 9:
        return "APPROVE"
    elif score >= 5:
        return "REVIEW"
    return "DECLINE"


def get_int_input(prompt: str) -> int:
    while True:
        value = input(prompt).strip()
        if value.lower() == "exit":
            raise KeyboardInterrupt
        try:
            return int(value)
        except ValueError:
            print("Please enter a valid whole number.")


def get_customer_type_input() -> str:
    while True:
        value = input("Customer type (h=homeowner, r=renter): ").strip().lower()
        if value == "exit":
            raise KeyboardInterrupt
        if value == "h":
            return "homeowner"
        if value == "r":
            return "renter"
        print("Invalid input. Please enter 'h' or 'r'.")


def get_resident_status_input() -> str:
    while True:
        value = input("Resident status (n=new, e=existing): ").strip().lower()
        if value == "exit":
            raise KeyboardInterrupt
        if value == "n":
            return "new"
        if value == "e":
            return "existing"
        print("Invalid input. Please enter 'n' or 'e'.")


def get_sell_plan_input() -> str:
    while True:
        value = input("Planning to sell the house soon? (y=yes, n=no): ").strip().lower()
        if value == "exit":
            raise KeyboardInterrupt
        if value == "y":
            return "yes"
        if value == "n":
            return "no"
        print("Invalid input. Please enter 'y' or 'n'.")


def get_renewal_input() -> str:
    while True:
        value = input("Likely to renew lease? (y=yes, n=no): ").strip().lower()
        if value == "exit":
            raise KeyboardInterrupt
        if value == "y":
            return "yes"
        if value == "n":
            return "no"
        print("Invalid input. Please enter 'y' or 'n'.")


def get_yes_no_input(prompt: str) -> str:
    while True:
        value = input(prompt).strip().lower()
        if value == "exit":
            raise KeyboardInterrupt
        if value == "y":
            return "yes"
        if value == "n":
            return "no"
        print("Invalid input. Please enter 'y' or 'n'.")


def get_state_input() -> str:
    while True:
        value = input("State abbreviation (example: CA, NY, KS): ").strip().upper()
        if value.lower() == "exit":
            raise KeyboardInterrupt
        if len(value) == 2 and value.isalpha():
            return value
        print("Invalid input. Please enter a 2-letter state abbreviation.")


def get_installation_cost_tier(state: str) -> str:
    return STATE_COST_MAP.get(state.upper(), "medium")


def get_installation_cost_from_tier(tier: str) -> int:
    return INSTALL_COST_TIERS[tier]


def calculate_demand_fit_score(customer: CustomerCase, plan: dict) -> tuple[int, str]:
    users = customer.household_size
    devices = customer.device_count
    speed = plan["speed_mbps"]

    if users <= 2 and devices <= 5:
        ideal_speed = 100
    elif users <= 4 and devices <= 10:
        ideal_speed = 300
    elif users <= 6:
        ideal_speed = 1000
    else:
        ideal_speed = 2000

    if speed == ideal_speed:
        return 2, "Plan closely matches expected household demand."
    elif speed > ideal_speed:
        return 1, "Plan exceeds expected demand (safe but potentially over-provisioned)."
    return -2, "Plan may underperform for household demand."


def build_customer_for_plan(base_customer: CustomerCase, plan: dict) -> CustomerCase:
    return CustomerCase(
        customer_name=base_customer.customer_name,
        customer_type=base_customer.customer_type,
        resident_status=base_customer.resident_status,
        current_provider=base_customer.current_provider,
        is_unhappy_with_current_provider=base_customer.is_unhappy_with_current_provider,
        planning_to_sell=base_customer.planning_to_sell,
        months_until_sale=base_customer.months_until_sale,
        lease_months_remaining=base_customer.lease_months_remaining,
        likely_to_renew=base_customer.likely_to_renew,
        credit_score=base_customer.credit_score,
        monthly_plan_value=plan["monthly_price"],
        installation_cost=base_customer.installation_cost,
        state=base_customer.state,
        installation_cost_tier=base_customer.installation_cost_tier,
        recommended_plan_name=plan["name"],
        recommended_plan_speed_mbps=plan["speed_mbps"],
        household_size=base_customer.household_size,
        device_count=base_customer.device_count,
    )


def evaluate_plan_options(base_customer: CustomerCase) -> list[dict]:
    evaluated_plans = []

    for plan in PLANS:
        temp_customer = build_customer_for_plan(base_customer, plan)
        score, _ = evaluate_risk(temp_customer)
        demand_score, demand_reason = calculate_demand_fit_score(temp_customer, plan)
        total_score = score + demand_score
        recommendation = get_recommendation(total_score)
        break_even_months = calculate_break_even_months(
            temp_customer.installation_cost, temp_customer.monthly_plan_value
        )

        evaluated_plans.append({
            "plan": plan,
            "base_score": score,
            "demand_score": demand_score,
            "score": total_score,
            "recommendation": recommendation,
            "break_even_months": break_even_months,
            "demand_reason": demand_reason,
        })

    return evaluated_plans


def choose_best_plan(evaluated_plans: list[dict]) -> dict:
    approve_plans = [p for p in evaluated_plans if p["recommendation"] == "APPROVE"]
    review_plans = [p for p in evaluated_plans if p["recommendation"] == "REVIEW"]

    if approve_plans:
        return min(approve_plans, key=lambda x: x["plan"]["monthly_price"])["plan"]
    if review_plans:
        return min(review_plans, key=lambda x: x["plan"]["monthly_price"])["plan"]

    return max(evaluated_plans, key=lambda x: x["score"])["plan"]


def build_plan_justification(chosen_plan: dict, evaluated_plans: list[dict]) -> list[str]:
    reasons = []

    matching = None
    for item in evaluated_plans:
        if item["plan"]["name"] == chosen_plan["name"]:
            matching = item
            break

    if matching is None:
        return ["Plan was selected by the engine."]

    recommendation = matching["recommendation"]
    break_even = matching["break_even_months"]

    if recommendation == "APPROVE":
        reasons.append("This is the lowest-cost plan that still meets approval criteria.")
    elif recommendation == "REVIEW":
        reasons.append("No plan fully met approval criteria, so this is the lowest-cost reviewable option.")
    else:
        reasons.append("No plan reached review or approval thresholds, so this is the highest-scoring fallback option.")

    reasons.append(f"This plan produces an estimated break-even period of {break_even:.1f} months.")
    reasons.append(matching["demand_reason"])

    faster_same_tier_options = [
        item for item in evaluated_plans
        if item["recommendation"] == recommendation
        and item["plan"]["monthly_price"] > chosen_plan["monthly_price"]
    ]
    if faster_same_tier_options:
        reasons.append("Higher-priced plans were available but were not necessary to achieve this decision tier.")

    cheaper_options = [
        item for item in evaluated_plans
        if item["plan"]["monthly_price"] < chosen_plan["monthly_price"]
    ]
    if cheaper_options:
        best_cheaper = max(cheaper_options, key=lambda x: x["score"])
        if best_cheaper["recommendation"] != recommendation:
            reasons.append(
                f"Cheaper plans performed worse, with the best cheaper option rated {best_cheaper['recommendation']}."
            )

    return reasons


def build_improvement_suggestions(result: dict) -> list[str]:
    customer = result["customer"]
    recommendation = result["recommendation"]
    suggestions = []
    break_even_months = result["break_even_months"]

    if recommendation == "APPROVE":
        suggestions.append("This case is already approved. Focus on execution and conversion.")
        return suggestions

    if customer.credit_score < 650:
        suggestions.append("Improving the customer credit profile into the 650+ range would strengthen the decision.")
    elif customer.credit_score < 750:
        suggestions.append("A stronger credit profile in the 750+ range would further improve confidence and approval odds.")

    if break_even_months > 12:
        suggestions.append("A shorter break-even period would help. This could come from lower installation cost or higher monthly revenue.")

    if customer.customer_type == "homeowner" and customer.planning_to_sell == "yes":
        needed_months = math.ceil(break_even_months)
        if customer.months_until_sale < break_even_months:
            suggestions.append(
                f"If the customer expected to stay at least {needed_months} months, the capital recovery outlook would improve."
            )

    if customer.customer_type == "renter":
        needed_months = math.ceil(break_even_months)
        if customer.lease_months_remaining < break_even_months:
            suggestions.append(
                f"A lease term or expected stay of at least {needed_months} months would improve the recovery case."
            )
        if customer.likely_to_renew == "no":
            suggestions.append("A likely renewal would improve retention confidence for this renter case.")

    if customer.current_provider != "none" and customer.is_unhappy_with_current_provider == "no":
        suggestions.append("A stronger switching trigger or clear dissatisfaction with the current provider would improve conversion likelihood.")

    demand_score, _ = calculate_demand_fit_score(
        customer,
        {"name": customer.recommended_plan_name, "speed_mbps": customer.recommended_plan_speed_mbps},
    )
    if demand_score < 0:
        suggestions.append("A higher-speed plan may better fit the household’s usage pattern and improve demand alignment.")

    if result["confidence"] == "Low":
        suggestions.append("Additional certainty on tenure, renewal likelihood, or move timing would improve confidence.")

    if not suggestions:
        suggestions.append("This case is close. Small improvements in economics or retention certainty could move it upward.")

    return suggestions


def create_base_customer_from_inputs(
    customer_name: str,
    customer_type: str,
    resident_status: str,
    household_size: int,
    device_count: int,
    current_provider: str,
    is_unhappy_with_current_provider: str,
    planning_to_sell: str,
    months_until_sale: int,
    lease_months_remaining: int,
    likely_to_renew: str,
    credit_score: int,
    state: str,
) -> CustomerCase:
    installation_cost_tier = get_installation_cost_tier(state)
    installation_cost = get_installation_cost_from_tier(installation_cost_tier)

    return CustomerCase(
        customer_name=customer_name,
        customer_type=customer_type,
        resident_status=resident_status,
        current_provider=current_provider,
        is_unhappy_with_current_provider=is_unhappy_with_current_provider,
        planning_to_sell=planning_to_sell,
        months_until_sale=months_until_sale,
        lease_months_remaining=lease_months_remaining,
        likely_to_renew=likely_to_renew,
        credit_score=credit_score,
        monthly_plan_value=0,
        installation_cost=installation_cost,
        state=state,
        installation_cost_tier=installation_cost_tier,
        recommended_plan_name="",
        recommended_plan_speed_mbps=0,
        household_size=household_size,
        device_count=device_count,
    )


def solve_customer(base_customer: CustomerCase) -> dict:
    evaluated_plans = evaluate_plan_options(base_customer)
    best_plan = choose_best_plan(evaluated_plans)
    plan_justification = build_plan_justification(best_plan, evaluated_plans)
    customer = build_customer_for_plan(base_customer, best_plan)

    base_score, _ = evaluate_risk(customer)
    demand_score, _ = calculate_demand_fit_score(
        customer,
        {"name": customer.recommended_plan_name, "speed_mbps": customer.recommended_plan_speed_mbps}
    )
    final_score = base_score + demand_score
    recommendation = get_recommendation(final_score)
    confidence_label, _ = calculate_confidence(customer)
    break_even_months = calculate_break_even_months(customer.installation_cost, customer.monthly_plan_value)

    result = {
        "customer": customer,
        "evaluated_plans": evaluated_plans,
        "plan_justification": plan_justification,
        "base_score": base_score,
        "demand_score": demand_score,
        "final_score": final_score,
        "recommendation": recommendation,
        "confidence": confidence_label,
        "break_even_months": break_even_months,
    }
    result["improvement_suggestions"] = build_improvement_suggestions(result)
    return result


def print_case_result(result: dict) -> None:
    customer = result["customer"]
    evaluated_plans = result["evaluated_plans"]
    plan_justification = result["plan_justification"]
    base_score = result["base_score"]
    demand_score = result["demand_score"]
    total_score = result["final_score"]
    recommendation = result["recommendation"]
    confidence_label = result["confidence"]
    break_even_months = result["break_even_months"]
    improvement_suggestions = result["improvement_suggestions"]

    _, reasons = evaluate_risk(customer)
    _, confidence_reasons = calculate_confidence(customer)
    _, demand_reason = calculate_demand_fit_score(
        customer,
        {"name": customer.recommended_plan_name, "speed_mbps": customer.recommended_plan_speed_mbps}
    )

    if break_even_months <= 6:
        recovery_label = "Fast recovery"
    elif break_even_months <= 12:
        recovery_label = "Moderate recovery"
    else:
        recovery_label = "Slow recovery"

    print("\n=== Fiber Investment Decision Summary ===")
    print(f"Customer: {customer.customer_name}")
    print(f"Customer Type: {customer.customer_type}")
    print(f"Resident Status: {customer.resident_status}")
    print(f"Household Size: {customer.household_size}")
    print(f"Active Devices: {customer.device_count}")
    print(f"State: {customer.state}")
    print(f"Installation Cost Tier: {customer.installation_cost_tier}")
    print(f"Current Provider: {customer.current_provider}")
    print(f"Unhappy with Current Provider: {customer.is_unhappy_with_current_provider}")

    if customer.customer_type == "homeowner":
        print(f"Planning to Sell Soon: {customer.planning_to_sell}")
        if customer.planning_to_sell == "yes":
            print(f"Months Until Sale: {customer.months_until_sale}")
    elif customer.customer_type == "renter":
        print(f"Lease Months Remaining: {customer.lease_months_remaining}")
        print(f"Likely to Renew Lease: {customer.likely_to_renew}")

    print(f"Credit Score: {customer.credit_score}")
    print(f"Recommended Plan: {customer.recommended_plan_name}")
    print(f"Plan Speed: {customer.recommended_plan_speed_mbps} Mbps")
    print(f"Monthly Plan Value: ${customer.monthly_plan_value:.2f}")
    print(f"Installation Cost: ${customer.installation_cost:.2f}")
    print(f"Break-even Period: {break_even_months:.1f} months")
    print(f"Recovery Speed: {recovery_label}")
    print(f"Base Risk Score: {base_score}/12")
    print(f"Demand Fit Adjustment: {demand_score:+d}")
    print(f"Final Investment Score: {total_score}")
    print(f"Recommendation: {recommendation}")
    print(f"Confidence: {confidence_label}")

    print("\nPlan Evaluation:")
    for item in evaluated_plans:
        print(
            f"  - {item['plan']['name']}: "
            f"BaseScore={item['base_score']}, "
            f"DemandAdj={item['demand_score']:+d}, "
            f"FinalScore={item['score']}, "
            f"Decision={item['recommendation']}, "
            f"Break-even={item['break_even_months']:.1f} months"
        )
        print(f"    Demand Fit: {item['demand_reason']}")

    print("\nPlan Justification:")
    for reason in plan_justification:
        print(f"  - {reason}")

    print("\nDecision Drivers:")
    for reason in reasons:
        print(f"  - {reason}")
    print(f"  - {demand_reason}")

    print("\nConfidence Drivers:")
    for reason in confidence_reasons:
        print(f"  - {reason}")

    print("\nWhat Would Improve This Decision:")
    for reason in improvement_suggestions:
        print(f"  - {reason}")

    print("=========================================\n")


def export_results_to_csv(results: list[dict], output_path: str) -> None:
    fieldnames = [
        "customer_name",
        "customer_type",
        "resident_status",
        "state",
        "household_size",
        "device_count",
        "current_provider",
        "credit_score",
        "recommended_plan_name",
        "recommended_plan_speed_mbps",
        "monthly_plan_value",
        "installation_cost",
        "installation_cost_tier",
        "break_even_months",
        "base_score",
        "demand_score",
        "final_score",
        "recommendation",
        "confidence",
        "improvement_suggestions",
    ]

    with open(output_path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            customer = result["customer"]
            writer.writerow({
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
                "monthly_plan_value": f"{customer.monthly_plan_value:.2f}",
                "installation_cost": f"{customer.installation_cost:.2f}",
                "installation_cost_tier": customer.installation_cost_tier,
                "break_even_months": f"{result['break_even_months']:.1f}",
                "base_score": result["base_score"],
                "demand_score": result["demand_score"],
                "final_score": result["final_score"],
                "recommendation": result["recommendation"],
                "confidence": result["confidence"],
                "improvement_suggestions": " | ".join(result["improvement_suggestions"]),
            })


def print_portfolio_summary(results: list[dict]) -> None:
    if not results:
        print("No portfolio results to summarize.")
        return

    recommendation_counts = Counter(r["recommendation"] for r in results)
    confidence_counts = Counter(r["confidence"] for r in results)
    plan_counts = Counter(r["customer"].recommended_plan_name for r in results)
    tier_counts = Counter(r["customer"].installation_cost_tier for r in results)

    total_install_cost = sum(r["customer"].installation_cost for r in results)
    avg_install_cost = total_install_cost / len(results)
    avg_break_even = sum(r["break_even_months"] for r in results) / len(results)
    avg_final_score = sum(r["final_score"] for r in results) / len(results)

    print("\n=== Portfolio Summary ===")
    print(f"Total customers evaluated: {len(results)}")

    print("\nRecommendation Mix:")
    for label in ["APPROVE", "REVIEW", "DECLINE"]:
        print(f"  - {label}: {recommendation_counts.get(label, 0)}")

    print("\nConfidence Mix:")
    for label in ["High", "Medium", "Low"]:
        print(f"  - {label}: {confidence_counts.get(label, 0)}")

    print("\nRecommended Plans:")
    for plan_name, count in plan_counts.items():
        print(f"  - {plan_name}: {count}")

    print("\nInstallation Cost Tiers:")
    for tier_name in ["low", "medium", "high"]:
        print(f"  - {tier_name}: {tier_counts.get(tier_name, 0)}")

    print("\nPortfolio Metrics:")
    print(f"  - Total Installation Cost: ${total_install_cost:,.2f}")
    print(f"  - Average Installation Cost: ${avg_install_cost:,.2f}")
    print(f"  - Average Break-even Period: {avg_break_even:.1f} months")
    print(f"  - Average Final Score: {avg_final_score:.1f}")

    print("\nCustomer Outcomes:")
    for r in results:
        customer = r["customer"]
        print(
            f"  - {customer.customer_name}: "
            f"{r['recommendation']} | "
            f"{r['confidence']} confidence | "
            f"{customer.recommended_plan_name} | "
            f"{r['break_even_months']:.1f} months"
        )

    print("=========================\n")


def run_sample_portfolio_mode() -> None:
    print("\nRunning sample portfolio simulation...\n")
    results = []

    for sample in SAMPLE_CUSTOMERS:
        base_customer = create_base_customer_from_inputs(
            customer_name=sample["customer_name"],
            customer_type=sample["customer_type"],
            resident_status=sample["resident_status"],
            household_size=sample["household_size"],
            device_count=sample["device_count"],
            current_provider=sample["current_provider"],
            is_unhappy_with_current_provider=sample["is_unhappy_with_current_provider"],
            planning_to_sell=sample["planning_to_sell"],
            months_until_sale=sample["months_until_sale"],
            lease_months_remaining=sample["lease_months_remaining"],
            likely_to_renew=sample["likely_to_renew"],
            credit_score=sample["credit_score"],
            state=sample["state"],
        )
        result = solve_customer(base_customer)
        results.append(result)

    print_portfolio_summary(results)
    output_path = "sample_portfolio_results.csv"
    export_results_to_csv(results, output_path)
    print(f"Portfolio results exported to: {output_path}\n")


def load_customers_from_csv(filepath: str) -> list[CustomerCase]:
    customers = []

    with open(filepath, mode="r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

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
                planning_to_sell = "no"
                months_until_sale = 0
                lease_months_remaining = 0
                likely_to_renew = "n/a"
            else:
                planning_to_sell = "n/a"
                months_until_sale = 0
                lease_months_remaining = 12
                likely_to_renew = "yes"

            base_customer = create_base_customer_from_inputs(
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
            customers.append(base_customer)

    return customers


def run_csv_portfolio_mode() -> None:
    filepath = input("Enter CSV file path: ").strip()
    if filepath.lower() == "exit":
        raise KeyboardInterrupt

    customers = load_customers_from_csv(filepath)
    results = [solve_customer(customer) for customer in customers]
    print_portfolio_summary(results)

    input_path = Path(filepath)
    output_path = input_path.with_name(f"{input_path.stem}_results.csv")
    export_results_to_csv(results, str(output_path))
    print(f"CSV evaluation results exported to: {output_path}\n")


def main() -> None:
    print("Fiber Investment Decision Tool")
    print("Type 'exit' at any prompt to quit.")
    print("Type 'portfolio' at customer name to run sample portfolio mode.")
    print("Type 'csv' at customer name to run CSV portfolio mode.\n")

    while True:
        try:
            name = input("Customer name: ").strip()
            if name.lower() == "exit":
                print("Goodbye.")
                break
            if name.lower() == "portfolio":
                run_sample_portfolio_mode()
                continue
            if name.lower() == "csv":
                run_csv_portfolio_mode()
                continue

            customer_type = get_customer_type_input()
            resident_status = get_resident_status_input()
            household_size = get_int_input("Number of people in household: ")
            device_count = get_int_input("Number of active devices: ")

            current_provider = input("Current provider (example: comcast, ziply, none): ").strip().lower()
            if current_provider == "exit":
                print("Goodbye.")
                break

            is_unhappy_with_current_provider = get_yes_no_input(
                "Unhappy with current provider? (y=yes, n=no): "
            )

            planning_to_sell = "n/a"
            months_until_sale = 0
            lease_months_remaining = 0
            likely_to_renew = "n/a"

            if customer_type == "homeowner":
                planning_to_sell = get_sell_plan_input()
                if planning_to_sell == "yes":
                    months_until_sale = get_int_input("In how many months do you expect to sell? ")
            elif customer_type == "renter":
                lease_months_remaining = get_int_input("How many months remain on current lease? ")
                likely_to_renew = get_renewal_input()

            credit_score = get_int_input("Credit score (300-850): ")
            state = get_state_input()

            base_customer = create_base_customer_from_inputs(
                customer_name=name,
                customer_type=customer_type,
                resident_status=resident_status,
                household_size=household_size,
                device_count=device_count,
                current_provider=current_provider,
                is_unhappy_with_current_provider=is_unhappy_with_current_provider,
                planning_to_sell=planning_to_sell,
                months_until_sale=months_until_sale,
                lease_months_remaining=lease_months_remaining,
                likely_to_renew=likely_to_renew,
                credit_score=credit_score,
                state=state,
            )

            result = solve_customer(base_customer)
            print_case_result(result)

        except KeyboardInterrupt:
            print("\nGoodbye.")
            break


if __name__ == "__main__":
    main()
