import {
  AGENT_ROUTES,
  TOOLS_BY_AGENT,
  isAgentRoute,
  type AgentRoute,
  type NodeId,
  type PipelineStep,
} from "@/lib/agent-graph";

export type NodeVisualState = "idle" | "active" | "done" | "error";

export interface PipelineState {
  nodeStates: Record<NodeId, NodeVisualState>;
  activeRoute: string | null;
  currentStep: PipelineStep | null;
  stepIndex: number;
  totalSteps: number;
  transcript: string;
  /** Edges highlighted on the graph (from → to). */
  activeEdges: Array<{ from: NodeId; to: NodeId }>;
  /** Tools invoked this turn (parallel — order does not matter). */
  usedTools: NodeId[];
}

const ALL_NODE_IDS: NodeId[] = [
  "input",
  "router",
  ...AGENT_ROUTES,
  "call_911",
  "notify_caregiver",
  "find_cool_space",
  "log_vital",
  "get_medications",
  "recall_history",
  "get_schedule",
  "mark_med_taken",
];

function idleNodes(): Record<NodeId, NodeVisualState> {
  return Object.fromEntries(
    ALL_NODE_IDS.map((id) => [id, "idle"]),
  ) as Record<NodeId, NodeVisualState>;
}

export function initialPipelineState(): PipelineState {
  return {
    nodeStates: idleNodes(),
    activeRoute: null,
    currentStep: null,
    stepIndex: 0,
    totalSteps: 0,
    transcript: "",
    activeEdges: [],
    usedTools: [],
  };
}

function edgesForUsedTools(route: AgentRoute, tools: NodeId[]): PipelineState["activeEdges"] {
  return tools.map((tool) => ({ from: route, to: tool }));
}

function setNode(
  states: Record<NodeId, NodeVisualState>,
  id: NodeId,
  visual: NodeVisualState,
): Record<NodeId, NodeVisualState> {
  return { ...states, [id]: visual };
}

function dimInactiveAgents(
  states: Record<NodeId, NodeVisualState>,
  route: string,
): Record<NodeId, NodeVisualState> {
  const next = { ...states };
  for (const agent of AGENT_ROUTES) {
    if (agent !== route && next[agent] === "idle") {
      next[agent] = "idle";
    }
  }
  return next;
}

/** Apply one pipeline step; previous active nodes on the path become done. */
export function applyStep(
  prev: PipelineState,
  step: PipelineStep,
  stepIndex: number,
  totalSteps: number,
): PipelineState {
  let nodeStates = { ...prev.nodeStates };
  let activeRoute = prev.activeRoute;
  let activeEdges: Array<{ from: NodeId; to: NodeId }> = [];
  let usedTools = [...prev.usedTools];
  let transcript = prev.transcript;

  switch (step.kind) {
    case "transcript":
      transcript = step.text;
      nodeStates = idleNodes();
      usedTools = [];
      nodeStates = setNode(nodeStates, "input", "active");
      activeEdges.push({ from: "input", to: "router" });
      break;

    case "routing_decision": {
      const route = step.routed_to;
      activeRoute = route;
      usedTools = [];
      nodeStates = setNode(nodeStates, "input", "done");
      nodeStates = setNode(nodeStates, "router", "active");
      if (isAgentRoute(route)) {
        nodeStates = dimInactiveAgents(nodeStates, route);
        nodeStates = setNode(nodeStates, route, "active");
        activeEdges.push({ from: "router", to: route });
      }
      break;
    }

    case "tool_invocation": {
      const tool = step.tool as NodeId;
      if (prev.activeRoute && isAgentRoute(prev.activeRoute)) {
        const route = prev.activeRoute;
        nodeStates = setNode(nodeStates, "router", "done");
        nodeStates = setNode(nodeStates, route, "active");
        if (ALL_NODE_IDS.includes(tool) && !usedTools.includes(tool)) {
          usedTools = [...usedTools, tool];
        }
        for (const t of usedTools) {
          nodeStates = setNode(nodeStates, t, "done");
        }
        activeEdges = edgesForUsedTools(route, usedTools);
      }
      break;
    }

    case "agent_reply": {
      const agent = step.agent;
      if (isAgentRoute(agent)) {
        nodeStates = setNode(nodeStates, "router", "done");
        nodeStates = setNode(nodeStates, agent, "done");
        activeRoute = agent;
        for (const t of TOOLS_BY_AGENT[agent]) {
          if (usedTools.includes(t) || nodeStates[t] !== "idle") {
            nodeStates = setNode(nodeStates, t, "done");
          }
        }
        activeEdges = edgesForUsedTools(agent, usedTools);
      }
      break;
    }
  }

  return {
    nodeStates,
    activeRoute,
    currentStep: step,
    stepIndex,
    totalSteps,
    transcript,
    activeEdges,
    usedTools,
  };
}

/** Fold a full scenario into final visual state (all steps applied). */
export function stateFromSteps(steps: PipelineStep[]): PipelineState {
  let state = initialPipelineState();
  steps.forEach((step, i) => {
    state = applyStep(state, step, i + 1, steps.length);
  });
  return state;
}

export function stepLabel(step: PipelineStep | null): string {
  if (!step) return "Idle — waiting for input";
  switch (step.kind) {
    case "transcript":
      return "Receiving patient input…";
    case "routing_decision":
      return `Routing → ${step.routed_to}`;
    case "tool_invocation":
      return `Tools in use: ${step.tool}()`;
    case "agent_reply":
      return `Reply from ${step.agent}`;
    default:
      return "Processing…";
  }
}
