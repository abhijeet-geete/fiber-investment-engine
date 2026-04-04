from dataclasses import dataclass


@dataclass
class CustomerCase:
    customer_name: str
    customer_type: str   # homeowner or renter
    resident_status: str   # new or existing
    current_provider: str
    is_unhappy_with_current_provider: str
    planning_to_sell: str
    months_until_sale: int
    lease_months_remaining: int
    likely_to_renew: str
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

    # Resident stability
    if customer.resident_status.lower() == "existing":
        score += 2
        reasons.append("Existing resident suggests greater stability.")
    elif customer.resident_status.lower() == "new":
        score += 1
        reasons.append("New resident may have less-established stay history.")
    else:
        reasons.append("Unknown resident status.")

    # Current provider context
    if customer.current_provider != "none":
        reasons.append(f"Customer currently uses {customer.current_provider}.")
    else:
        reasons.append("Customer does not currently have an internet provider.")

    # Switching likelihood
    if customer.current_provider != "none" and customer.is_unhappy_with_current_provider == "yes":
        score += 2
        reasons.append("Customer is unhappy with current provider, which may improve switching likelihood.")
    elif customer.current_provider != "none" and customer.is_unhappy_with_current_provider == "no":
        score -= 1
        reasons.append("Customer appears satisfied with current provider, which may reduce switching likelihood.")

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
        reasons.append("Recovery period is long, which increases risk.")

    # Customer time horizon vs break-even
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


def get_float_input(prompt: str) -> float:
    while True:
        value = input(prompt).strip()
        if value.lower() == "exit":
            raise KeyboardInterrupt
        try:
            return float(value)
        except ValueError:
            print("Please enter a valid number.")


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

def main() -> None:
    print("Fiber Investment Decision Tool")
    print("Type 'exit' at any prompt to quit.\n")

    while True:
        try:
            name = input("Customer name: ").strip()
            if name.lower() == "exit":
                print("Goodbye.")
                break

            customer_type = get_customer_type_input()

            resident_status = get_resident_status_input()

            current_provider = input("Current provider (example: comcast, ziply, none): ").strip().lower()
            if current_provider == "exit":
                print("Goodbye.")
                break

            while True:
                unhappy_input = input("Unhappy with current provider? (y=yes, n=no): ").strip().lower()

                if unhappy_input == "exit":
                    raise KeyboardInterrupt
                elif unhappy_input == "y":
                    is_unhappy_with_current_provider = "yes"
                    break
                elif unhappy_input == "n":
                    is_unhappy_with_current_provider = "no"
                    break
                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

            
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
            monthly_plan_value = get_float_input("Monthly plan value ($): ")
            installation_cost = get_float_input("Installation cost ($): ")

            customer = CustomerCase(
                customer_name=name,
                customer_type=customer_type,
                resident_status=resident_status,
                current_provider=current_provider,
                is_unhappy_with_current_provider=is_unhappy_with_current_provider,
                planning_to_sell=planning_to_sell,
                months_until_sale=months_until_sale,
                lease_months_remaining=lease_months_remaining,
                likely_to_renew=likely_to_renew,
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
    print(f"Resident Status: {customer.resident_status}")
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
    print(f"Monthly Plan Value: ${customer.monthly_plan_value:.2f}")
    print(f"Installation Cost: ${customer.installation_cost:.2f}")
    print(f"Break-even Period: {break_even_months:.1f} months")
    print(f"Recovery Speed: {recovery_label}")
    print(f"Investment Score: {score}/12")
    print(f"Recommendation: {recommendation}")

    print("\nDecision Drivers:")
    for reason in reasons:
        print(f"  - {reason}")

    print("=========================================\n")


if __name__ == "__main__":
    main()