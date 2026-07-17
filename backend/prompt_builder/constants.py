"""Constants for the prompt builder package."""

from __future__ import annotations

MAX_TOP_VALUES_IN_CONTEXT = 3

RESPONSE_CONTRACT_SUCCESS = "success"
RESPONSE_CONTRACT_CLARIFICATION = "clarification"
RESPONSE_CONTRACT_ERROR = "error"

RESPONSE_CONTRACT_TEMPLATE = """
Your response must be valid JSON only, with exactly one of these structures:

Success:
{
  "status": "success",
  "title": "Short chart title",
  "python": "Generated Python code here"
}

Clarification:
{
  "status": "clarification",
  "message": "What you need the user to clarify"
}

Error:
{
  "status": "error",
  "message": "Error description"
}
"""