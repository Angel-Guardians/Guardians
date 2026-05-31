/** Static Guardian agent/tool topology — mirrors backend/agents/guardian.py + tool bindings. */

export type NodeKind = "input" | "router" | "agent" | "tool";

export type NodeId =
  | "input"
  | "router"
  | "safety"
  | "health"
  | "reminder"
  | "companion"
  | "behavior"
  | "caregiver"
  | "call_person"
  | "call_911"
  | "notify_caregiver"
  | "find_cool_space"
  | "log_vital"
  | "get_medications"
  | "recall_history"
  | "get_schedule"
  | "mark_med_taken";

export interface GraphNode {
  id: NodeId;
  kind: NodeKind;
  label: string;
  /** Specialist route id when kind === "agent". */
  routeId?: string;
}

export interface GraphEdge {
  from: NodeId;
  to: NodeId;
}

export const AGENT_ROUTES = [
  "safety",
  "health",
  "reminder",
  "companion",
  "behavior",
  "caregiver",
] as const;

export type AgentRoute = (typeof AGENT_ROUTES)[number];

/** Tools each specialist may invoke (backend/agents/*.py tool_names). */
export const TOOLS_BY_AGENT: Record<AgentRoute, NodeId[]> = {
  safety: ["call_person", "find_cool_space"],
  health: ["log_vital", "get_medications", "recall_history", "find_cool_space"],
  reminder: ["get_schedule", "mark_med_taken", "recall_history"],
  companion: ["recall_history", "find_cool_space"],
  behavior: ["call_person", "recall_history"],
  caregiver: ["notify_caregiver", "recall_history"],
};

export const AGENT_GRAPH = {
  nodes: [
    { id: "input", kind: "input", label: "Patient input" },
    { id: "router", kind: "router", label: "Guardian router" },
    {
      id: "safety",
      kind: "agent",
      label: "Safety",
      routeId: "safety",
    },
    {
      id: "health",
      kind: "agent",
      label: "Health",
      routeId: "health",
    },
    {
      id: "reminder",
      kind: "agent",
      label: "Reminder",
      routeId: "reminder",
    },
    {
      id: "companion",
      kind: "agent",
      label: "Companion",
      routeId: "companion",
    },
    {
      id: "behavior",
      kind: "agent",
      label: "Behavior",
      routeId: "behavior",
    },
    {
      id: "caregiver",
      kind: "agent",
      label: "Caregiver liaison",
      routeId: "caregiver",
    },
    { id: "call_person", kind: "tool", label: "call_person" },
    { id: "call_911", kind: "tool", label: "call_911" },
    { id: "notify_caregiver", kind: "tool", label: "notify_caregiver" },
    { id: "find_cool_space", kind: "tool", label: "find_cool_space" },
    { id: "log_vital", kind: "tool", label: "log_vital" },
    { id: "get_medications", kind: "tool", label: "get_medications" },
    { id: "recall_history", kind: "tool", label: "recall_history" },
    { id: "get_schedule", kind: "tool", label: "get_schedule" },
    { id: "mark_med_taken", kind: "tool", label: "mark_med_taken" },
  ] satisfies GraphNode[],
  edges: [
    { from: "input", to: "router" },
    ...AGENT_ROUTES.map(
      (route) =>
        ({ from: "router", to: route }) as GraphEdge,
    ),
    ...(Object.entries(TOOLS_BY_AGENT) as [AgentRoute, NodeId[]][]).flatMap(
      ([agent, tools]) =>
        tools.map((tool) => ({ from: agent, to: tool }) as GraphEdge),
    ),
  ] satisfies GraphEdge[],
};

export type PipelineStep =
  | { kind: "transcript"; text: string }
  | { kind: "routing_decision"; routed_to: AgentRoute | string }
  | { kind: "tool_invocation"; tool: string }
  | { kind: "agent_reply"; agent: AgentRoute | string };

export interface DemoScenario {
  id: string;
  label: string;
  description: string;
  inputText: string;
  steps: PipelineStep[];
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "fall",
    label: "Fall emergency",
    description: "Routes to Safety, calls 911 and notifies caregiver.",
    inputText: "I fell and my chest feels tight",
    steps: [
      { kind: "transcript", text: "I fell and my chest feels tight" },
      { kind: "routing_decision", routed_to: "safety" },
      { kind: "tool_invocation", tool: "call_person" },
      { kind: "agent_reply", agent: "safety" },
    ],
  },
  {
    id: "medication",
    label: "Medication",
    description: "Routes to Reminder and checks schedule.",
    inputText: "Did I take my morning pills?",
    steps: [
      { kind: "transcript", text: "Did I take my morning pills?" },
      { kind: "routing_decision", routed_to: "reminder" },
      { kind: "tool_invocation", tool: "get_schedule" },
      { kind: "agent_reply", agent: "reminder" },
    ],
  },
  {
    id: "chat",
    label: "Chat",
    description: "Routes to Companion with memory recall.",
    inputText: "Tell me about my granddaughter",
    steps: [
      { kind: "transcript", text: "Tell me about my granddaughter" },
      { kind: "routing_decision", routed_to: "companion" },
      { kind: "tool_invocation", tool: "recall_history" },
      { kind: "agent_reply", agent: "companion" },
    ],
  },
];

export function isAgentRoute(id: string): id is AgentRoute {
  return (AGENT_ROUTES as readonly string[]).includes(id);
}

export function toolsForRoute(route: string): NodeId[] {
  if (isAgentRoute(route)) return TOOLS_BY_AGENT[route];
  return [];
}
