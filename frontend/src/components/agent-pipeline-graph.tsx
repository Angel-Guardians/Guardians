"use client";

import {
  MessageCircle,
  Pill,
  Play,
  RotateCcw,
  Shield,
  Workflow,
} from "lucide-react";

import {
  AGENT_GRAPH,
  AGENT_ROUTES,
  DEMO_SCENARIOS,
  TOOLS_BY_AGENT,
  type AgentRoute,
  type DemoScenario,
  type NodeId,
} from "@/lib/agent-graph";
import type { PipelineState } from "@/lib/pipeline-state";
import { stepLabel } from "@/lib/pipeline-state";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const CANVAS_H = 720;
const AGENT_ROW_GAP = 88;
const TOOL_NODE_H = 44;
/** Center-to-center spacing — must exceed node height to avoid overlap. */
const TOOL_STACK_GAP = TOOL_NODE_H + 20;

const STAGE_X = {
  input: 130,
  router: 360,
  agents: 580,
  tools: 800,
} as const;

const STAGE_LABELS = [
  { x: STAGE_X.input, label: "Input" },
  { x: STAGE_X.router, label: "Router" },
  { x: STAGE_X.agents, label: "Specialists" },
  { x: STAGE_X.tools, label: "Tools (parallel)" },
] as const;

const AGENT_ACCENT: Record<AgentRoute, string> = {
  safety: "#ef4444",
  health: "#3b82f6",
  reminder: "#22c55e",
  companion: "#a855f7",
  behavior: "#f97316",
  caregiver: "#64748b",
};

interface NodeLayout {
  cx: number;
  cy: number;
  w: number;
  h: number;
}

function agentRowY(index: number): number {
  const totalSpan = (AGENT_ROUTES.length - 1) * AGENT_ROW_GAP;
  const top = (CANVAS_H - totalSpan) / 2;
  return top + index * AGENT_ROW_GAP;
}

function buildLayouts(activeRoute: AgentRoute | null): Record<NodeId, NodeLayout> {
  const layouts = {} as Record<NodeId, NodeLayout>;
  const midY = CANVAS_H / 2;

  layouts.input = { cx: STAGE_X.input, cy: midY, w: 156, h: 52 };
  layouts.router = { cx: STAGE_X.router, cy: midY, w: 176, h: 56 };

  AGENT_ROUTES.forEach((route, i) => {
    layouts[route] = {
      cx: STAGE_X.agents,
      cy: agentRowY(i),
      w: 124,
      h: 50,
    };
  });

  if (activeRoute) {
    const tools = TOOLS_BY_AGENT[activeRoute];
    const agentCy = layouts[activeRoute].cy;
    tools.forEach((toolId, i) => {
      layouts[toolId] = {
        cx: STAGE_X.tools,
        cy: agentCy + (i - (tools.length - 1) / 2) * TOOL_STACK_GAP,
        w: 148,
        h: TOOL_NODE_H,
      };
    });
  }

  return layouts;
}

function isToolForAgent(toolId: NodeId, route: AgentRoute | null): boolean {
  return route !== null && TOOLS_BY_AGENT[route].includes(toolId);
}

function canvasWidth(layouts: Record<NodeId, NodeLayout>): number {
  let maxRight = STAGE_X.agents + 80;
  for (const layout of Object.values(layouts)) {
    maxRight = Math.max(maxRight, layout.cx + layout.w / 2 + 48);
  }
  return Math.max(1180, maxRight);
}

function getLayout(
  id: NodeId,
  layouts: Record<NodeId, NodeLayout>,
): NodeLayout {
  return layouts[id] ?? { cx: 0, cy: 0, w: 80, h: 36 };
}

const ARROW_SIZE = 9;

/** Line stops before the arrowhead; tip sits on the target node's left edge. */
function edgeGeometry(
  from: NodeLayout,
  to: NodeLayout,
): { linePath: string; arrowPath: string } {
  const x1 = from.cx + from.w / 2;
  const y1 = from.cy;
  const tipX = to.cx - to.w / 2;
  const y2 = to.cy;
  const xLineEnd = tipX - ARROW_SIZE;
  const dx = xLineEnd - x1;

  let linePath: string;
  if (Math.abs(y2 - y1) < 6) {
    linePath = `M ${x1} ${y1} L ${xLineEnd} ${y2}`;
  } else {
    const bend = Math.min(56, Math.abs(dx) * 0.4);
    const c1x = x1 + bend;
    const c2x = xLineEnd - bend;
    linePath = `M ${x1} ${y1} C ${c1x} ${y1}, ${c2x} ${y2}, ${xLineEnd} ${y2}`;
  }

  const half = ARROW_SIZE / 2;
  const arrowPath = `M ${tipX - ARROW_SIZE} ${y2 - half} L ${tipX} ${y2} L ${tipX - ARROW_SIZE} ${y2 + half} Z`;

  return { linePath, arrowPath };
}

function isEdgeActive(
  from: NodeId,
  to: NodeId,
  activeEdges: PipelineState["activeEdges"],
): boolean {
  return activeEdges.some((e) => e.from === from && e.to === to);
}

function routeColor(route: AgentRoute | null): string {
  return route ? AGENT_ACCENT[route] : "var(--foreground)";
}

/** Node receives the route accent only after routing picks a specialist. */
function isOnPath(
  nodeId: NodeId,
  visual: PipelineState["nodeStates"][NodeId],
  route: AgentRoute | null,
  usedTools: NodeId[],
): boolean {
  if (visual === "idle" || !route) return false;
  if (nodeId === "input" || nodeId === "router") return true;
  if (nodeId === route) return true;
  return usedTools.includes(nodeId);
}

function isEdgeOnPath(
  from: NodeId,
  to: NodeId,
  route: AgentRoute | null,
  states: PipelineState["nodeStates"],
  usedTools: NodeId[],
): boolean {
  if (!route) return false;
  if (from === "input" && to === "router") {
    return states.input !== "idle" || states.router !== "idle";
  }
  if (from === "router" && to === route) {
    return states.router !== "idle" || states[route] !== "idle";
  }
  if (from === route) {
    return usedTools.includes(to as NodeId);
  }
  return false;
}

interface AgentPipelineGraphProps {
  pipeline: PipelineState;
  onRunDemo?: (scenario: DemoScenario) => void;
  onReset?: () => void;
  isPlaying?: boolean;
  activeScenarioId?: string | null;
}

export function AgentPipelineGraph({
  pipeline,
  onRunDemo,
  onReset,
  isPlaying = false,
  activeScenarioId = null,
}: AgentPipelineGraphProps) {
  const route = pipeline.activeRoute;
  const emphasizedAgent =
    route && AGENT_ROUTES.includes(route as AgentRoute)
      ? (route as AgentRoute)
      : null;

  const layouts = buildLayouts(emphasizedAgent);
  const canvasW = canvasWidth(layouts);

  const edges = AGENT_GRAPH.edges.filter((e) => {
    if (e.from === "input" || e.from === "router") return true;
    if (!emphasizedAgent) return false;
    return (e.from as AgentRoute) === emphasizedAgent;
  });

  const progressPct =
    pipeline.totalSteps > 0
      ? Math.round((pipeline.stepIndex / pipeline.totalSteps) * 100)
      : 0;

  const pathColor = emphasizedAgent ? routeColor(emphasizedAgent) : undefined;

  return (
    <div className="overflow-hidden rounded-2xl border bg-card shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Workflow className="size-4 text-muted-foreground" />
          Pipeline flow
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {pathColor ? (
            <span className="flex items-center gap-1.5">
              <span
                className="size-2 rounded-full"
                style={{ backgroundColor: pathColor }}
              />
              Route: {emphasizedAgent}
            </span>
          ) : null}
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-muted-foreground/30" />
            Idle
          </span>
        </div>
      </div>

      <div className="w-full overflow-x-auto overflow-y-hidden p-4 sm:p-6">
        <svg
          viewBox={`0 0 ${canvasW} ${CANVAS_H}`}
          width={canvasW}
          height={CANVAS_H}
          className="mx-auto block min-h-[400px]"
          style={{ minWidth: canvasW }}
          role="img"
          aria-label="Guardian agent pipeline graph"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <linearGradient id="canvas-bg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--card)" />
              <stop offset="100%" stopColor="var(--muted)" stopOpacity="0.35" />
            </linearGradient>
            <pattern
              id="dot-grid"
              width="20"
              height="20"
              patternUnits="userSpaceOnUse"
            >
              <circle
                cx="1"
                cy="1"
                r="0.75"
                className="fill-muted-foreground/25"
              />
            </pattern>
          </defs>

          <rect width={canvasW} height={CANVAS_H} fill="url(#canvas-bg)" />
          <rect width={canvasW} height={CANVAS_H} fill="url(#dot-grid)" />

          {STAGE_LABELS.map(({ x, label }) => (
            <text
              key={label}
              x={x}
              y={28}
              textAnchor="middle"
              className="fill-muted-foreground font-sans text-[11px] font-semibold uppercase tracking-widest"
            >
              {label}
            </text>
          ))}

          {AGENT_GRAPH.nodes.map((node) => {
            const isTool = node.kind === "tool";
            if (isTool && !isToolForAgent(node.id, emphasizedAgent)) {
              return null;
            }

            const layout = getLayout(node.id, layouts);
            const visual = pipeline.nodeStates[node.id] ?? "idle";
            const isAgent = node.kind === "agent";
            const dimAgent =
              isAgent &&
              emphasizedAgent &&
              node.routeId !== emphasizedAgent &&
              visual === "idle";
            const toolUsed =
              isTool &&
              emphasizedAgent &&
              pipeline.usedTools.includes(node.id);

            const x = layout.cx - layout.w / 2;
            const y = layout.cy - layout.h / 2;
            const onPath = isOnPath(
              node.id,
              visual,
              emphasizedAgent,
              pipeline.usedTools,
            );
            const lit = visual !== "idle" && !dimAgent;
            const stroke = toolUsed
              ? routeColor(emphasizedAgent)
              : isTool && emphasizedAgent
                ? "var(--border)"
                : onPath
                  ? routeColor(emphasizedAgent)
                  : lit
                    ? "var(--foreground)"
                    : "var(--border)";
            const strokeWidth = toolUsed
              ? 2.5
              : isTool && emphasizedAgent
                ? 1.5
                : onPath && visual === "active"
                  ? 3
                  : onPath && visual === "done"
                    ? 2
                    : lit
                      ? 1.75
                      : 1.25;
            const strokeOpacity = toolUsed ? 1 : onPath && visual === "done" ? 0.55 : 1;

            return (
              <g
                key={node.id}
                className={cn(
                  "transition-all duration-500",
                  dimAgent ? "opacity-25" : "opacity-100",
                )}
              >
                <rect
                  x={x}
                  y={y}
                  width={layout.w}
                  height={layout.h}
                  rx={10}
                  fill="var(--card)"
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  strokeOpacity={strokeOpacity}
                />
                <text
                  x={layout.cx}
                  y={layout.cy}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill={
                    toolUsed || onPath || lit
                      ? "var(--foreground)"
                      : "var(--muted-foreground)"
                  }
                  className={cn(
                    "pointer-events-none select-none font-sans",
                    (toolUsed || onPath || lit) && "font-semibold",
                    isTool && "font-mono",
                  )}
                  fontSize={
                    node.kind === "router" ? 14 : isAgent ? 12.5 : 11
                  }
                >
                  {node.label}
                </text>
              </g>
            );
          })}

          {edges.map((edge) => {
            const fromL = getLayout(edge.from, layouts);
            const toL = getLayout(edge.to, layouts);
            const active = isEdgeActive(
              edge.from,
              edge.to,
              pipeline.activeEdges,
            );
            const onPathEdge = isEdgeOnPath(
              edge.from,
              edge.to,
              emphasizedAgent,
              pipeline.nodeStates,
              pipeline.usedTools,
            );
            const edgeColor = onPathEdge
              ? routeColor(emphasizedAgent)
              : "var(--border)";
            const { linePath, arrowPath } = edgeGeometry(fromL, toL);
            const strokeOpacity = active ? 1 : onPathEdge ? 0.7 : 0.45;
            const strokeWidth = active ? 2.5 : onPathEdge ? 2 : 1.25;

            return (
              <g key={`${edge.from}-${edge.to}`} pointerEvents="none">
                <path
                  d={linePath}
                  fill="none"
                  stroke={edgeColor}
                  strokeOpacity={strokeOpacity}
                  strokeWidth={strokeWidth}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeDasharray={active ? "10 6" : undefined}
                  className={active ? "animate-pulse" : undefined}
                />
                <path
                  d={arrowPath}
                  fill={edgeColor}
                  fillOpacity={strokeOpacity}
                  stroke="none"
                />
              </g>
            );
          })}
        </svg>
      </div>

      {pipeline.transcript ? (
        <div className="border-t border-border/50 bg-muted/15 px-4 py-2.5 text-center text-sm">
          <span className="font-medium text-foreground">Patient: </span>
          <span className="text-muted-foreground">
            &ldquo;{pipeline.transcript}&rdquo;
          </span>
        </div>
      ) : null}

      {onRunDemo ? (
        <div className="border-t bg-muted/10 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium">Try a demo flow</p>
            {pipeline.totalSteps > 0 ? (
              <div className="flex min-w-[140px] flex-1 max-w-xs items-center gap-2 sm:max-w-sm">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                <span className="shrink-0 font-mono text-xs text-muted-foreground">
                  {pipeline.stepIndex}/{pipeline.totalSteps}
                </span>
              </div>
            ) : (
              <span className="text-xs text-muted-foreground">
                {stepLabel(pipeline.currentStep)}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {DEMO_SCENARIOS.map((preset) => {
              const Icon =
                preset.id === "fall"
                  ? Shield
                  : preset.id === "medication"
                    ? Pill
                    : MessageCircle;
              const isActive = activeScenarioId === preset.id;
              return (
                <Button
                  key={preset.id}
                  type="button"
                  variant={isActive ? "default" : "outline"}
                  size="sm"
                  disabled={isPlaying && !isActive}
                  className={cn(
                    "gap-1.5 shadow-sm",
                    isActive && "ring-2 ring-primary/30",
                  )}
                  onClick={() => onRunDemo(preset)}
                >
                  <Icon className="size-3.5" />
                  {preset.label}
                </Button>
              );
            })}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="gap-1.5 text-muted-foreground"
              disabled={isPlaying}
              onClick={onReset}
            >
              <RotateCcw className="size-3.5" />
              Reset
            </Button>
            <Button
              type="button"
              size="sm"
              className="ml-auto gap-1.5"
              disabled={isPlaying}
              onClick={() => {
                const fall = DEMO_SCENARIOS[0];
                if (fall) onRunDemo(fall);
              }}
            >
              <Play className="size-3.5 fill-current" />
              Play demo
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
