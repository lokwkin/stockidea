import { useState, useRef, useEffect, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { Bot, Send, Loader2, ChevronDown, ChevronRight, TrendingUp, TrendingDown, Activity } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ChatMessage, AgentEvent, BacktestScores } from "@/types/agent"
import type { StrategyDetail, StrategyBacktestSummary } from "@/types/strategy"

// --- Reusable components from AgentView ---

function ScoreCard({ scores, rule, profitPct, baselinePct }: {
  scores: BacktestScores
  rule?: string
  profitPct?: number
  baselinePct?: number
}) {
  return (
    <div className="rounded-lg border bg-card/50 p-4 space-y-3">
      {rule && (
        <div className="text-xs">
          <span className="text-muted-foreground">Rule: </span>
          <code className="text-primary/80 bg-primary/10 px-1.5 py-0.5 rounded text-xs">{rule}</code>
        </div>
      )}
      {profitPct !== undefined && (
        <div className="flex gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Return: </span>
            <span className={cn("font-semibold", profitPct >= 0 ? "text-positive" : "text-destructive")}>
              {profitPct >= 0 ? "+" : ""}{profitPct.toFixed(1)}%
            </span>
          </div>
          {baselinePct !== undefined && (
            <div>
              <span className="text-muted-foreground">Baseline: </span>
              <span className={cn("font-semibold", baselinePct >= 0 ? "text-positive" : "text-destructive")}>
                {baselinePct >= 0 ? "+" : ""}{baselinePct.toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      )}
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs">Sharpe</div>
          <div className={cn("font-semibold", scores.sharpe_ratio >= 1 ? "text-positive" : "text-foreground")}>
            {scores.sharpe_ratio.toFixed(2)}
          </div>
        </div>
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs">Sortino</div>
          <div className="font-semibold">{scores.sortino_ratio.toFixed(2)}</div>
        </div>
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs">Calmar</div>
          <div className="font-semibold">{scores.calmar_ratio.toFixed(2)}</div>
        </div>
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs">Win Rate</div>
          <div className={cn("font-semibold", scores.win_rate >= 0.5 ? "text-positive" : "text-destructive")}>
            {(scores.win_rate * 100).toFixed(0)}%
          </div>
        </div>
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs">Max DD</div>
          <div className="font-semibold text-destructive">{scores.max_drawdown_pct.toFixed(1)}%</div>
        </div>
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs">Rebalances</div>
          <div className="font-semibold">{scores.total_rebalances}</div>
        </div>
      </div>
    </div>
  )
}

function ToolCallCard({ name, input }: { name: string; input: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm text-primary/80 w-full text-left"
      >
        <Activity className="h-3.5 w-3.5 flex-shrink-0" />
        <span className="font-medium">Running {name}</span>
        {expanded ? <ChevronDown className="h-3.5 w-3.5 ml-auto" /> : <ChevronRight className="h-3.5 w-3.5 ml-auto" />}
      </button>
      {expanded && (
        <pre className="mt-2 text-xs text-muted-foreground overflow-x-auto">
          {JSON.stringify(input, null, 2)}
        </pre>
      )}
    </div>
  )
}

function MessageBubble({ message, backtestIndex }: { message: ChatMessage; backtestIndex?: number }) {
  if (message.type === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg bg-primary/20 px-4 py-3 text-sm">
          {message.content}
        </div>
      </div>
    )
  }

  if (message.type === "text") {
    return (
      <div className="flex gap-3">
        <div className="flex-shrink-0 mt-1">
          <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center">
            <Bot className="h-3.5 w-3.5 text-primary" />
          </div>
        </div>
        <div className="text-sm whitespace-pre-wrap leading-relaxed max-w-[85%]">{message.content}</div>
      </div>
    )
  }

  if (message.type === "tool_call") {
    return (
      <div className="ml-9">
        <ToolCallCard name={message.name} input={message.input} />
      </div>
    )
  }

  if (message.type === "tool_result") {
    const { result, name } = message
    if (name === "run_backtest" && result.scores) {
      return (
        <div className="ml-9">
          <div className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1.5">
            {result.profit_pct !== undefined && result.profit_pct >= (result.baseline_profit_pct ?? 0) ? (
              <TrendingUp className="h-3 w-3 text-positive" />
            ) : (
              <TrendingDown className="h-3 w-3 text-destructive" />
            )}
            Backtest {backtestIndex !== undefined ? `#${backtestIndex}` : ""} Result
          </div>
          <ScoreCard
            scores={result.scores}
            rule={result.rule as string | undefined}
            profitPct={result.profit_pct}
            baselinePct={result.baseline_profit_pct}
          />
        </div>
      )
    }
    return (
      <div className="ml-9">
        <div className="rounded-lg border bg-card/50 p-3 text-xs text-muted-foreground">
          {name} completed
        </div>
      </div>
    )
  }

  if (message.type === "error") {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        {message.message}
      </div>
    )
  }

  return null
}

// --- Strategy comparison table ---

function BacktestComparisonTable({ backtests }: { backtests: StrategyBacktestSummary[] }) {
  if (backtests.length === 0) return null

  // Find best by Sharpe
  let bestIdx = 0
  let bestSharpe = -Infinity
  backtests.forEach((bt, i) => {
    const sharpe = bt.scores?.sharpe_ratio ?? -Infinity
    if (sharpe > bestSharpe) {
      bestSharpe = sharpe
      bestIdx = i
    }
  })

  return (
    <div className="border-t pt-4 mt-4">
      <h3 className="text-sm font-semibold mb-3">Backtest Iterations</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b text-muted-foreground">
              <th className="py-2 px-2 text-left">#</th>
              <th className="py-2 px-2 text-left">Rule</th>
              <th className="py-2 px-2 text-right">Return</th>
              <th className="py-2 px-2 text-right">Sharpe</th>
              <th className="py-2 px-2 text-right">Sortino</th>
              <th className="py-2 px-2 text-right">Max DD</th>
              <th className="py-2 px-2 text-right">Win Rate</th>
              <th className="py-2 px-2 text-right"></th>
            </tr>
          </thead>
          <tbody>
            {backtests.map((bt, i) => (
              <tr
                key={bt.id}
                className={cn(
                  "border-b hover:bg-muted/50 transition-colors",
                  i === bestIdx && "bg-primary/5 font-medium"
                )}
              >
                <td className="py-2 px-2">{i + 1}</td>
                <td className="py-2 px-2 max-w-[200px] truncate">
                  <code className="text-xs bg-muted px-1 py-0.5 rounded">{bt.rule}</code>
                </td>
                <td className={cn("py-2 px-2 text-right", bt.profit_pct >= 0 ? "text-positive" : "text-destructive")}>
                  {bt.profit_pct >= 0 ? "+" : ""}{bt.profit_pct.toFixed(1)}%
                </td>
                <td className="py-2 px-2 text-right">{bt.scores?.sharpe_ratio.toFixed(2) ?? "—"}</td>
                <td className="py-2 px-2 text-right">{bt.scores?.sortino_ratio.toFixed(2) ?? "—"}</td>
                <td className="py-2 px-2 text-right text-destructive">{bt.scores?.max_drawdown_pct.toFixed(1) ?? "—"}%</td>
                <td className="py-2 px-2 text-right">{bt.scores ? `${(bt.scores.win_rate * 100).toFixed(0)}%` : "—"}</td>
                <td className="py-2 px-2 text-right">
                  <Link
                    to={`/backtest/${bt.id}`}
                    className="text-primary hover:underline"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// --- Parse persisted messages into ChatMessage[] ---

function parseStrategyMessages(strategy: StrategyDetail): ChatMessage[] {
  const result: ChatMessage[] = []

  for (const msg of strategy.messages) {
    if (msg.role === "user") {
      try {
        const parsed = JSON.parse(msg.content_json)
        result.push({ type: "user", content: parsed.text || "" })
      } catch {
        result.push({ type: "user", content: msg.content_json })
      }
    } else if (msg.role === "assistant") {
      try {
        const events: AgentEvent[] = JSON.parse(msg.content_json)
        for (const evt of events) {
          if (evt.event === "text") {
            result.push({ type: "text", content: evt.data.content })
          } else if (evt.event === "tool_call") {
            result.push({ type: "tool_call", name: evt.data.name, input: evt.data.input })
          } else if (evt.event === "tool_result") {
            result.push({ type: "tool_result", name: evt.data.name, result: evt.data.result })
          } else if (evt.event === "error") {
            result.push({ type: "error", message: evt.data.message })
          }
        }
      } catch {
        // Skip unparseable messages
      }
    }
  }

  return result
}

// --- Main StrategyView ---

export function StrategyView() {
  const { id } = useParams<{ id: string }>()
  const [strategy, setStrategy] = useState<StrategyDetail | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [followUp, setFollowUp] = useState("")
  const [isRunning, setIsRunning] = useState(false)
  const [loading, setLoading] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Load strategy on mount
  useEffect(() => {
    if (!id) return
    let cancelled = false

    fetch(`/api/strategies/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("Strategy not found")
        return res.json()
      })
      .then((data: StrategyDetail) => {
        if (cancelled) return
        setStrategy(data)
        setMessages(parseStrategyMessages(data))
        setIsRunning(data.status === "running")
        setLoading(false)
      })
      .catch((err) => {
        if (cancelled) return
        console.error(err)
        setLoading(false)
      })

    return () => { cancelled = true }
  }, [id])

  // Process SSE stream from a response
  const processSSEStream = useCallback(async (response: Response) => {
    const reader = response.body?.getReader()
    if (!reader) return

    const decoder = new TextDecoder()
    let buffer = ""

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = ""

        let currentEvent = ""
        let currentData = ""

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7)
          } else if (line.startsWith("data: ")) {
            currentData = line.slice(6)
          } else if (line === "" && currentEvent && currentData) {
            try {
              const parsed: AgentEvent = {
                event: currentEvent as AgentEvent["event"],
                data: JSON.parse(currentData),
              }

              if (parsed.event === "text") {
                setMessages((prev) => [...prev, { type: "text", content: parsed.data.content }])
              } else if (parsed.event === "tool_call") {
                setMessages((prev) => [
                  ...prev,
                  { type: "tool_call", name: parsed.data.name, input: parsed.data.input },
                ])
              } else if (parsed.event === "tool_result") {
                setMessages((prev) => [
                  ...prev,
                  { type: "tool_result", name: parsed.data.name, result: parsed.data.result },
                ])
              } else if (parsed.event === "error") {
                setMessages((prev) => [...prev, { type: "error", message: parsed.data.message }])
              }
              // "done" and "strategy_created" — just let the stream end
            } catch {
              // Skip malformed events
            }
            currentEvent = ""
            currentData = ""
          } else if (line !== "") {
            buffer = lines.slice(lines.indexOf(line)).join("\n")
            break
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setMessages((prev) => [...prev, { type: "error", message: `Connection error: ${err}` }])
      }
    }
  }, [])

  const handleFollowUp = useCallback(async () => {
    if (!followUp.trim() || isRunning || !id) return

    const userMessage = followUp.trim()
    setFollowUp("")
    setMessages((prev) => [...prev, { type: "user", content: userMessage }])
    setIsRunning(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch(`/api/strategies/${id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction: userMessage }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const err = await response.text()
        setMessages((prev) => [...prev, { type: "error", message: `Request failed: ${err}` }])
        setIsRunning(false)
        return
      }

      await processSSEStream(response)
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setMessages((prev) => [...prev, { type: "error", message: `Connection error: ${err}` }])
      }
    } finally {
      setIsRunning(false)
      abortRef.current = null
      // Refresh strategy data to get updated backtests
      if (id) {
        fetch(`/api/strategies/${id}`)
          .then((res) => res.ok ? res.json() : null)
          .then((data: StrategyDetail | null) => {
            if (data) setStrategy(data)
          })
          .catch(() => {})
      }
    }
  }, [followUp, isRunning, id, processSSEStream])

  const handleStop = useCallback(() => {
    abortRef.current?.abort()
    setIsRunning(false)
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && e.altKey) {
        e.preventDefault()
        handleFollowUp()
      }
    },
    [handleFollowUp]
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!strategy) {
    return (
      <div className="flex items-center justify-center h-screen text-muted-foreground">
        Strategy not found
      </div>
    )
  }

  // Count backtest results for numbering
  let simIndex = 0

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex-shrink-0 border-b px-6 py-4">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
          <Bot className="h-7 w-7 text-primary" />
          {strategy.name}
        </h1>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-sm text-muted-foreground">
            {strategy.date_start} to {strategy.date_end}
          </span>
          <span className="text-xs text-muted-foreground/60">
            {strategy.model}
          </span>
          <span className={cn(
            "text-xs px-1.5 py-0.5 rounded-full",
            strategy.status === "idle" && "bg-green-100 text-green-700",
            strategy.status === "running" && "bg-blue-100 text-blue-700",
            strategy.status === "failed" && "bg-red-100 text-red-700",
          )}>
            {strategy.status}
          </span>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && !isRunning && (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground/60 space-y-3">
            <Bot className="h-16 w-16" />
            <p className="text-sm">Waiting for agent response...</p>
          </div>
        )}

        {messages.map((msg, i) => {
          let si: number | undefined
          if (msg.type === "tool_result" && msg.name === "run_backtest" && msg.result.scores) {
            simIndex++
            si = simIndex
          }
          return <MessageBubble key={i} message={msg} backtestIndex={si} />
        })}

        {isRunning && messages.length > 0 && (
          <div className="flex gap-3 items-center ml-9">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="text-sm text-muted-foreground">Thinking...</span>
          </div>
        )}

        {/* Backtest comparison table */}
        {strategy.backtests.length > 0 && (
          <BacktestComparisonTable backtests={strategy.backtests} />
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Follow-up input */}
      <div className="flex-shrink-0 px-6 py-4 border-t">
        <div className="flex gap-3">
          <textarea
            value={followUp}
            onChange={(e) => setFollowUp(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Send a follow-up instruction... (Option+Enter to send)"
            className={cn(
              "flex-1 rounded-lg border bg-background px-4 py-3 text-sm resize-none",
              "placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30",
              "min-h-[50px] max-h-[100px]"
            )}
            disabled={isRunning}
            rows={2}
          />
          {isRunning ? (
            <button
              onClick={handleStop}
              className="flex-shrink-0 rounded-lg bg-destructive/20 text-destructive hover:bg-destructive/30 px-4 py-2 text-sm font-medium transition-colors self-end"
            >
              Stop
            </button>
          ) : (
            <button
              onClick={handleFollowUp}
              disabled={!followUp.trim()}
              className={cn(
                "flex-shrink-0 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium transition-colors self-end",
                "hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed",
                "flex items-center gap-2"
              )}
            >
              <Send className="h-4 w-4" />
              Send
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
