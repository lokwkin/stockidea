export interface AgentTextEvent {
  event: "text"
  data: { content: string }
}

export interface AgentToolCallEvent {
  event: "tool_call"
  data: { name: string; input: Record<string, unknown> }
}

export interface AgentToolResultEvent {
  event: "tool_result"
  data: {
    name: string
    result: {
      rule?: string
      profit_pct?: number
      baseline_profit_pct?: number
      scores?: SimulationScores
      error?: string
      fields?: IndicatorField[]
      [key: string]: unknown
    }
  }
}

export interface AgentDoneEvent {
  event: "done"
  data: Record<string, never>
}

export interface AgentErrorEvent {
  event: "error"
  data: { message: string }
}

export type AgentEvent =
  | AgentTextEvent
  | AgentToolCallEvent
  | AgentToolResultEvent
  | AgentDoneEvent
  | AgentErrorEvent

export interface SimulationScores {
  sharpe_ratio: number
  sortino_ratio: number
  calmar_ratio: number
  max_drawdown_pct: number
  max_drawdown_duration_weeks: number
  win_rate: number
  avg_win_pct: number
  avg_loss_pct: number
  total_rebalances: number
}

export interface IndicatorField {
  name: string
  type: string
  description: string
}

// UI message types for rendering the chat
export type ChatMessage =
  | { type: "user"; content: string }
  | { type: "text"; content: string }
  | { type: "tool_call"; name: string; input: Record<string, unknown> }
  | { type: "tool_result"; name: string; result: AgentToolResultEvent["data"]["result"] }
  | { type: "error"; message: string }
