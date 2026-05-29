"""Tier 1 - the Orchestrator.

Hears every event, runs the Risk Classifier, routes to a sub-agent,
holds the conversational floor lock, brokers cross-agent handoffs.
See ARCHITECTURE.md sec. 3 + sec. 5.
"""
