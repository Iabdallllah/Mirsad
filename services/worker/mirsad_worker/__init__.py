"""Mirsad worker package.

Phase 0 (Foundation): configuration + idle entrypoint. Phase 1 adds the
code-level egress/SSRF guard (``mirsad_worker.egress``) and the deterministic
PII sanitizer (``mirsad_worker.sanitizer``). The queue consumer, crawler, and
LangGraph agents are still pending (plan.md §3.2). The idle entrypoint itself
performs no outbound requests and touches no customer data.
"""
