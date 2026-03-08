"""
app/ai/prompts.py
──────────────────
Prompt templates for the AI classification engine.
Prompts are versioned — changing a prompt is a significant engineering event.
Templates are functions, not strings, so they can be unit tested.
"""

from datetime import datetime


SYSTEM_PROMPT = """You are an expert fraud analyst and operations specialist for a cryptocurrency exchange.
Your role is to classify incoming support tickets and operational events with precision.

You must analyze each ticket and return a structured JSON classification.

CLASSIFICATION CATEGORIES:
- withdrawal_issue: Problems with withdrawals (pending, failed, delayed)
- wallet_access: User cannot access wallet, login issues, 2FA problems
- suspicious_transaction: Unusual transaction patterns, unauthorized transfers
- account_access: Account locked, compromised, or inaccessible
- transaction_failure: Technical transaction errors, network issues
- fraud_report: Explicit reports of fraud, theft, or scam
- general_inquiry: General questions not fitting other categories

PRIORITY LEVELS:
- critical: Immediate threat to funds or security breach in progress
- high: Significant financial impact or strong fraud indicators
- medium: Moderate impact, needs attention within hours
- low: Minor issues, informational, can be handled in normal queue

FRAUD SCORE (0.0 to 1.0):
- 0.0–0.2: No fraud indicators
- 0.2–0.4: Mild anomalies, monitor
- 0.4–0.6: Suspicious patterns, investigate
- 0.6–0.8: Strong fraud indicators, flag for review
- 0.8–1.0: High confidence fraud activity

RESPONSE FORMAT:
You must respond with ONLY valid JSON matching this exact structure:
{
  "category": "<category>",
  "priority": "<priority>",
  "fraud_score": <float between 0.0 and 1.0>,
  "reason": "<detailed reasoning explaining your classification>"
}

Do not include any text before or after the JSON. Do not use markdown code blocks."""


def build_classification_prompt(
    user_id: str,
    wallet_address: str | None,
    transaction_id: str | None,
    message: str,
    ticket_timestamp: datetime,
    historical_context: str | None = None,
) -> str:
    """
    Build the user message for ticket classification.

    Args:
        user_id: The submitting user's ID
        wallet_address: Associated wallet (may be None)
        transaction_id: Associated transaction (may be None)
        message: The user's issue description
        ticket_timestamp: When the ticket was created
        historical_context: Optional summary of prior tickets for this wallet
    """
    prompt_parts = [
        "TICKET TO CLASSIFY:",
        f"User ID: {user_id}",
        f"Timestamp: {ticket_timestamp.isoformat()}",
    ]

    if wallet_address:
        prompt_parts.append(f"Wallet Address: {wallet_address}")

    if transaction_id:
        prompt_parts.append(f"Transaction ID: {transaction_id}")

    prompt_parts.append(f"\nUser Message:\n{message}")

    if historical_context:
        prompt_parts.extend([
            "\nHISTORICAL CONTEXT FOR THIS WALLET:",
            historical_context,
            "\nNote: Consider this history when assessing fraud probability.",
        ])

    prompt_parts.append(
        "\nClassify this ticket and respond with JSON only."
    )

    return "\n".join(prompt_parts)


def build_historical_context(
    complaint_count: int,
    failed_tx_count: int,
    prior_fraud_flags: int,
    days_window: int = 30,
) -> str | None:
    """
    Build a historical context summary string for the AI prompt.
    Returns None if no history (keeps prompt shorter).
    """
    if complaint_count == 0 and failed_tx_count == 0 and prior_fraud_flags == 0:
        return None

    parts = [f"In the last {days_window} days for this wallet:"]

    if complaint_count > 0:
        parts.append(f"- {complaint_count} prior complaint ticket(s)")
    if failed_tx_count > 0:
        parts.append(f"- {failed_tx_count} failed transaction(s)")
    if prior_fraud_flags > 0:
        parts.append(f"- {prior_fraud_flags} existing fraud flag(s)")

    return "\n".join(parts)
