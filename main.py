from dataclasses import dataclass


@dataclass
class CustomerCase:
    customer_name: str
    customer_type: str   # homeowner or renter
    credit_score: int
    monthly_plan_value: float
    installation_cost: float


def calculate_break_even_months(installation_cost: float, monthly_plan_value: float) -> float:
    if monthly_plan_value <= 0:
        return 0
    return installation_cost / monthly_plan_value


def evaluate_risk(customer: CustomerCase) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    # Customer type
    if customer.customer_type.lower() == "homeowner":
        score += 2
        reasons.append("Homeowner is generally more stable.")
    elif customer.customer_type.lower() == "renter":
        score += 0
        reasons.append("Renter may have higher move-out risk.")
    else:
        reasons.append("Unknown customer type.")

    # Credit score
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

    # Break-even logic
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
        score += 0
        reasons.append("Recovery period is long, which increases risk.")

    return score, reasons


def get_recommendation(score: int) -> str:
    if score >= 7:
        return "APPROVE"
    elif score >= 4:
        return "REVIEW"
    return "DECLINE"


def print_case_result(customer: CustomerCase) -> None:
    break_even_months = calculate_break_even_months(
        customer.installation_cost, customer.monthly_plan_value
    )
    score, reasons = evaluate_risk(customer)
    recommendation = get_recommendation(score)

    print("\n--- Fiber Investment Decision Report ---")
    print(f"Customer: {customer.customer_name}")
    print(f"Customer Type: {customer.customer_type}")
    print(f"Credit Score: {customer.credit_score}")
    print(f"Monthly Plan Value: ${customer.monthly_plan_value:.2f}")
    print(f"Installation Cost: ${customer.installation_cost:.2f}")
    print(f"Break-even Period: {break_even_months:.1f} months")
    print(f"Investment Score: {score}/8")
    print(f"Recommendation: {recommendation}")

    print("\nReasons:")
    for reason in reasons:
        print(f"  - {reason}")
    print("----------------------------------------\n")


def get_int_input(prompt: str) -> int:
    while True:
        value = input(prompt).strip()
        if value.lower() == "exit":
            raise KeyboardInterrupt
        try:
            return int(value)
        except ValueError:
            print("Please enter a valid whole number.")


def get_float_input(prompt: str) -> float:
    while True:
        value = input(prompt).strip()
        if value.lower() == "exit":
            raise KeyboardInterrupt
        try:
            return float(value)
        except ValueError:
            print("Please enter a valid number.")

def main() -> None:
    print("Fiber Investment Decision Tool")
    print("Type 'exit' at any prompt to quit.\n")

    while True:
        try:
            name = input("Customer name: ").strip()
            if name.lower() == "exit":
                print("Goodbye.")
                break

            customer_type = input("Customer type (homeowner/renter): ").strip()
            if customer_type.lower() == "exit":
                print("Goodbye.")
                break

            credit_score = get_int_input("Credit score (300-850): ")
            monthly_plan_value = get_float_input("Monthly plan value ($): ")
            installation_cost = get_float_input("Installation cost ($): ")

            customer = CustomerCase(
                customer_name=name,
                customer_type=customer_type,
                credit_score=credit_score,
                monthly_plan_value=monthly_plan_value,
                installation_cost=installation_cost,
            )

            print_case_result(customer)

        except KeyboardInterrupt:
            print("\nGoodbye.")
            break

def print_case_result(customer: CustomerCase) -> None:
    break_even_months = calculate_break_even_months(
        customer.installation_cost, customer.monthly_plan_value
    )
    score, reasons = evaluate_risk(customer)
    recommendation = get_recommendation(score)

    if break_even_months <= 6:
        recovery_label = "Fast recovery"
    elif break_even_months <= 12:
        recovery_label = "Moderate recovery"
    else:
        recovery_label = "Slow recovery"

    print("\n=== Fiber Investment Decision Summary ===")
    print(f"Customer: {customer.customer_name}")
    print(f"Customer Type: {customer.customer_type}")
    print(f"Credit Score: {customer.credit_score}")
    print(f"Monthly Plan Value: ${customer.monthly_plan_value:.2f}")
    print(f"Installation Cost: ${customer.installation_cost:.2f}")
    print(f"Break-even Period: {break_even_months:.1f} months")
    print(f"Recovery Speed: {recovery_label}")
    print(f"Investment Score: {score}/8")
    print(f"Recommendation: {recommendation}")

    print("\nDecision Drivers:")
    for reason in reasons:
        print(f"  - {reason}")

    print("=========================================\n")


if __name__ == "__main__":
    main()