"""LangGraph Supervisor - the top-tier router.

Subscribes to the event bus. For each event:
  1. Run the Risk Classifier to assign a SeverityTier
  2. Run the hybrid router to pick the sub-agent
  3. Acquire the floor lock if the sub-agent will speak
  4. Invoke the sub-agent's subgraph
  5. Persist the routing decision to the Event Log
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from backend.events.types import GuardianEvent

if TYPE_CHECKING:
    from backend.agents.base import SubAgent
    from backend.events.bus import EventBus
    from backend.orchestrator.risk_classifier import RiskClassifier
    from backend.orchestrator.router import Router


class Orchestrator:
    """The top-tier supervisor. One instance per process."""

    def __init__(
        self,
        bus: "EventBus",
        router: "Router",
        risk_classifier: "RiskClassifier",
        sub_agents: dict[str, "SubAgent"],
    ) -> None:
        self.bus = bus
        self.router = router
        self.risk_classifier = risk_classifier
        self.sub_agents = sub_agents
        # TODO: floor_lock = FloorLock()

    async def handle(self, event: GuardianEvent) -> None:
        """Single entry point: every event flows through here."""
        # 1. Risk classification
        event.severity = await self.risk_classifier.classify(event)

        # 2. Route
        target = await self.router.route(event)

        # 3. Floor lock if speaking
        # TODO: acquire lock if target will hold the mic

        # 4. Invoke the sub-agent
        agent = self.sub_agents[target]
        await agent.handle(event)

        # 5. Log the routing decision
        # TODO: publish RoutingDecisionEvent

    async def start(self) -> None:
        self.bus.subscribe(self.handle)
        await self.bus.start()
