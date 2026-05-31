"use client";

import {
  AGENT_GRAPH,
  AGENT_ROUTES,
  TOOLS_BY_AGENT,
  type AgentRoute,
  type NodeId,
} from "@/lib/agent-graph";
import type { PipelineState } from "@/lib/pipeline-state";
import { cn } from "@/lib/utils";

const W = 920;
const H = 400;

const POSITIONS: Record<NodeId, { x: number; y: number }> = {
  input: { x: W / 2, y: 36 },
  router: { x: W / 2, y: 88 },
  safety: { x: 80, y: 168 },
  health: { x: 210, y: 168 },
  reminder: { x: 340, y: 168 },
  companion: { x: 470, y: 168 },
  behavior: { x: 600, y: 168 },
  caregiver: { x: 730, y: 168 },
  call_911: { x: 50, y: 288 },
  notify_caregiver: { x: 400, y: 352 },
  find_cool_space: { x: 120, y: 328 },
  log_vital: { x: 180, y: 288 },
  get_medications: { x: 240, y: 328 },
  get_schedule: { x: 310, y: 288 },
  mark_med_taken: { x: 370, y: 328 },
  recall_history: { x: 470, y: 328 },
};

function pos(id: NodeId): { x: number; y: number } {
  return POSITIONS[id];
}

function edgePath(from: NodeId, to: NodeId): string {
  const a = pos(from);
  const b = pos(to);
  const midY = (a.y + b.y) / 2;
  return `M ${a.x} ${a.y} C ${a.x} ${midY}, ${b.x} ${midY}, ${b.x} ${b.y}`;
}

function isEdgeActive(
  from: NodeId,
  to: NodeId,
  activeEdges: PipelineState["activeEdges"],
): boolean {
  return activeEdges.some((e) => e.from === from && e.to === to);
}

function nodeStateClass(state: PipelineState["nodeStates"][NodeId]): string {
  switch (state) {
    case "active":
      return "border-primary bg-primary/10 text-primary shadow-sm ring-2 ring-primary/40";
    case "done":
      return "border-green-600/50 bg-green-500/10 text-foreground dark:border-green-500/40";
    case "error":
      return "border-destructive bg-destructive/10 text-destructive";
    default:
      return "border-border bg-muted/30 text-muted-foreground opacity-60";
  }
}

interface AgentPipelineGraphProps {
  pipeline: PipelineState;
}

export function AgentPipelineGraph({ pipeline }: AgentPipelineGraphProps) {
  const route = pipeline.activeRoute;
  const emphasizedAgent =
    route && AGENT_ROUTES.includes(route as AgentRoute)
      ? (route as AgentRoute)
      : null;

  const edges = AGENT_GRAPH.edges.filter((e) => {
    if (e.from === "router" || e.from === "input") return true;
    if (e.to in TOOLS_BY_AGENT) {
      const agent = e.from as AgentRoute;
      if (!emphasizedAgent) return false;
      return agent === emphasizedAgent;
    }
    return false;
  });

  return (
    <div className="w-full overflow-x-auto rounded-2xl border bg-card/50 p-2">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="mx-auto h-auto min-h-[280px] w-full max-w-[920px]"
        role="img"
        aria-label="Guardian agent pipeline graph"
      >
        <defs>
          <marker
            id="arrow"
            markerWidth="8"
            markerHeight="8"
            refX="6"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L8,4 L0,8 Z" className="fill-muted-foreground" />
          </marker>
          <marker
            id="arrow-active"
            markerWidth="8"
            markerHeight="8"
            refX="6"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L8,4 L0,8 Z" className="fill-primary" />
          </marker>
        </defs>

        {edges.map((edge) => {
          const active = isEdgeActive(
            edge.from,
            edge.to,
            pipeline.activeEdges,
          );
          const fromDone =
            pipeline.nodeStates[edge.from] === "done" ||
            pipeline.nodeStates[edge.from] === "active";
          const highlight = active || fromDone;
          return (
            <path
              key={`${edge.from}-${edge.to}`}
              d={edgePath(edge.from, edge.to)}
              fill="none"
              markerEnd={highlight ? "url(#arrow-active)" : "url(#arrow)"}
              className={cn(
                "transition-all duration-300",
                active
                  ? "stroke-primary stroke-[2.5] [stroke-dasharray:6_4] animate-pulse"
                  : highlight
                    ? "stroke-primary/50 stroke-[1.5]"
                    : "stroke-border stroke-1",
              )}
            />
          );
        })}

        {AGENT_GRAPH.nodes.map((node) => {
          const { x, y } = pos(node.id);
          const visual = pipeline.nodeStates[node.id] ?? "idle";
          const isTool = node.kind === "tool";
          const isAgent = node.kind === "agent";
          const dimTool =
            isTool &&
            emphasizedAgent &&
            !TOOLS_BY_AGENT[emphasizedAgent].includes(node.id);
          const dimAgent =
            isAgent &&
            emphasizedAgent &&
            node.routeId !== emphasizedAgent &&
            visual === "idle";

          const w = isTool ? 88 : isAgent ? 72 : node.id === "router" ? 100 : 90;
          const h = isTool ? 28 : 36;

          return (
            <g
              key={node.id}
              transform={`translate(${x - w / 2}, ${y - h / 2})`}
              className={cn(dimTool || dimAgent ? "opacity-25" : "opacity-100")}
            >
              <foreignObject width={w} height={h} className="overflow-visible">
                <div
                  className={cn(
                    "flex h-full w-full items-center justify-center rounded-md border px-1 text-center font-mono text-[10px] leading-tight transition-all duration-300",
                    node.kind === "router" && "text-xs font-sans font-semibold",
                    node.kind === "input" && "text-xs font-sans",
                    isAgent && "text-[11px] font-sans font-medium",
                    nodeStateClass(visual),
                  )}
                >
                  {node.label}
                </div>
              </foreignObject>
            </g>
          );
        })}
      </svg>

      {pipeline.transcript ? (
        <p className="border-t px-3 py-2 text-center text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Input: </span>
          &ldquo;{pipeline.transcript}&rdquo;
        </p>
      ) : null}
    </div>
  );
}
