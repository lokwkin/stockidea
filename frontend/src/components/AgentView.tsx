import { useState, useRef, useEffect, useCallback } from "react"
import { Bot, Send, Loader2, ChevronDown, ChevronRight, TrendingUp, TrendingDown, Activity } from "lucide-react"
import { cn } from "@/lib/utils"
import type { ChatMessage, AgentEvent, BacktestScores } from "@/types/agent"

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
        <Loader2 className="h-3.5 w-3.5 animate-spin ml-auto flex-shrink-0" />
        {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
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
    // Generic tool result (e.g. list_indicator_fields)
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

export function AgentView() {
  const [instruction, setInstruction] = useState("")
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleRun = useCallback(async () => {
    if (!instruction.trim() || isRunning) return

    const userInstruction = instruction.trim()
    setInstruction("")
    setMessages([{ type: "user", content: userInstruction }])
    setIsRunning(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch("/api/agent/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction: userInstruction }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const err = await response.text()
        setMessages((prev) => [...prev, { type: "error", message: `Request failed: ${err}` }])
        setIsRunning(false)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        setMessages((prev) => [...prev, { type: "error", message: "No response body" }])
        setIsRunning(false)
        return
      }

      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE events from buffer
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
            // End of event
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
              // "done" — just let the stream end
            } catch {
              // Skip malformed events
            }
            currentEvent = ""
            currentData = ""
          } else if (line !== "") {
            // Incomplete event, keep in buffer
            buffer = lines.slice(lines.indexOf(line)).join("\n")
            break
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setMessages((prev) => [...prev, { type: "error", message: `Connection error: ${err}` }])
      }
    } finally {
      setIsRunning(false)
      abortRef.current = null
    }
  }, [instruction, isRunning])

  const handleStop = useCallback(() => {
    abortRef.current?.abort()
    setIsRunning(false)
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Submit on Alt+Enter (matching user keybinding preference)
      if (e.key === "Enter" && e.altKey) {
        e.preventDefault()
        handleRun()
      }
    },
    [handleRun]
  )

  // Count backtest results for numbering
  let simIndex = 0

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex-shrink-0 border-b px-6 py-4">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
          <Bot className="h-7 w-7 text-primary" />
          AI Strategy Agent
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Describe your strategy idea and the agent will design, backtest, and iterate to find the best rule.
        </p>
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 px-6 py-4 border-b">
        <div className="flex gap-3">
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. I want a momentum strategy that avoids volatile stocks and big drawdowns..."
            className={cn(
              "flex-1 rounded-lg border bg-background px-4 py-3 text-sm resize-none",
              "placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30",
              "min-h-[60px] max-h-[120px]"
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
              onClick={handleRun}
              disabled={!instruction.trim()}
              className={cn(
                "flex-shrink-0 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium transition-colors self-end",
                "hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed",
                "flex items-center gap-2"
              )}
            >
              <Send className="h-4 w-4" />
              Run
            </button>
          )}
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && !isRunning && (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground/60 space-y-3">
            <Bot className="h-16 w-16" />
            <p className="text-sm">Enter a strategy idea to get started</p>
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

        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}
