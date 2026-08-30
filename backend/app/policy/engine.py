from typing import Literal

PolicyDecisionType = Literal["ALLOW", "WARNING", "REDACT", "REGENERATE", "BLOCK", "HUMAN_REVIEW"]

class PolicyDecisionResult:
    def __init__(self, decision: PolicyDecisionType, reason: str = "", version: str = "v1.0.0"):
        self.decision = decision
        self.reason = reason
        self.version = version

class PolicyEngine:
    def evaluate_request(self, messages: list[dict]) -> PolicyDecisionResult:
        # Phase 1: Default to ALLOW. Advanced Phase 2-3 rules excluded.
        return PolicyDecisionResult(decision="ALLOW", reason="Default allow policy")

    def evaluate_response_chunk(self, chunk: str) -> PolicyDecisionResult:
        # Phase 1: Default to ALLOW.
        return PolicyDecisionResult(decision="ALLOW", reason="Default allow policy")

policy_engine = PolicyEngine()
