import { useState, useEffect, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { Bot, Send, Loader2, ChevronDown, ChevronRight, TrendingUp, TrendingDown, Activity } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"
import type { ChatMessage, AgentEvent, BacktestScores } from "@/types/agent"
import type { StrategyDetail, StrategyBacktestSummary } from "@/types/strategy"

const POLL_INTERVAL_MS = 2000

// --- Reusable components from AgentView ---

function ScoreCard({ scores, rule, sortExpr, maxStocks, rebalanceWeeks, indexName, profitPct, baselinePct }: {
  scores: BacktestScores
  rule?: string
  sortExpr?: string
  maxStocks?: number
  rebalanceWeeks?: number
  indexName?: string
  profitPct?: number
  baselinePct?: number
}) {
  return (
    <div className="rounded-lg border bg-muted p-4 space-y-3">
      {rule && (
        <div className="text-xs">
          <span className="text-muted-foreground">Rule: </span>
          <code className="text-primary/80 bg-primary/10 px-1.5 py-0.5 rounded text-xs">{rule}</code>
        </div>
      )}
      {sortExpr && (
        <div className="text-xs">
          <span className="text-muted-foreground">Sort: </span>
          <code className="text-primary/80 bg-primary/10 px-1.5 py-0.5 rounded text-xs">{sortExpr}</code>
        </div>
      )}
      {(maxStocks !== undefined || rebalanceWeeks !== undefined || indexName) && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {indexName && (<div><span>Index: </span><span className="text-foreground font-medium">{indexName}</span></div>)}
          {maxStocks !== undefined && (<div><span>Max stocks: </span><span className="text-foreground font-medium">{maxStocks}</span></div>)}
          {rebalanceWeeks !== undefined && (<div><span>Rebalance: </span><span className="text-foreground font-medium">{rebalanceWeeks}w</span></div>)}
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
          <div className="text-muted-foreground text-xs font-medium uppercase tracking-wide">Sharpe</div>
          <div className={cn("font-semibold", scores.sharpe_ratio >= 1 ? "text-positive" : "text-foreground")}>
            {scores.sharpe_ratio.toFixed(2)}
          </div>
        </div>
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs font-medium uppercase tracking-wide">Sortino</div>
          <div className="font-semibold">{scores.sortino_ratio.toFixed(2)}</div>
        </div>
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs font-medium uppercase tracking-wide">Calmar</div>
          <div className="font-semibold">{scores.calmar_ratio.toFixed(2)}</div>
        </div>
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs font-medium uppercase tracking-wide">Win Rate</div>
          <div className={cn("font-semibold", scores.win_rate >= 0.5 ? "text-positive" : "text-destructive")}>
            {(scores.win_rate * 100).toFixed(0)}%
          </div>
        </div>
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs font-medium uppercase tracking-wide">Max DD</div>
          <div className="font-semibold text-destructive">{scores.max_drawdown_pct.toFixed(1)}%</div>
        </div>
        <div className="space-y-1">
          <div className="text-muted-foreground text-xs font-medium uppercase tracking-wide">Rebalances</div>
          <div className="font-semibold">{scores.total_rebalances}</div>
        </div>
      </div>
    </div>
  )
}

function ToolCallCard({ name, input }: { name: string; input: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="rounded-lg border bg-muted p-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm text-muted-foreground w-full text-left"
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

function MarkdownText({ content }: { content: string }) {
  return (
    <div className="text-sm leading-relaxed max-w-[85%] space-y-2 [&_p]:m-0 [&_p+p]:mt-2">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="text-lg font-bold mt-3 mb-1">{children}</h1>,
          h2: ({ children }) => <h2 className="text-base font-bold mt-3 mb-1">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1">{children}</h3>,
          h4: ({ children }) => <h4 className="text-sm font-semibold mt-2 mb-1">{children}</h4>,
          h5: ({ children }) => <h5 className="text-xs font-semibold uppercase tracking-wide mt-2 mb-1">{children}</h5>,
          h6: ({ children }) => <h6 className="text-xs font-semibold uppercase tracking-wide mt-2 mb-1">{children}</h6>,
          strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="list-disc pl-5 space-y-0.5 my-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 space-y-0.5 my-1">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-primary/40 pl-3 italic text-muted-foreground my-2">
              {children}
            </blockquote>
          ),
          code: ({ className, children }) => {
            const isBlock = className?.includes("language-")
            if (isBlock) {
              return (
                <pre className="bg-muted rounded-md p-3 overflow-x-auto my-2 text-xs">
                  <code className={className}>{children}</code>
                </pre>
              )
            }
            return (
              <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">{children}</code>
            )
          },
          pre: ({ children }) => <>{children}</>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
              {children}
            </a>
          ),
          hr: () => <hr className="my-3 border-border" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

function MessageBubble({ message, backtestIndex }: { message: ChatMessage; backtestIndex?: number }) {
  if (message.type === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg bg-info-bg px-4 py-3 text-sm">
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
        <MarkdownText content={message.content} />
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
            sortExpr={result.sort_expr as string | undefined}
            maxStocks={result.max_stocks as number | undefined}
            rebalanceWeeks={result.rebalance_interval_weeks as number | undefined}
            indexName={result.index as string | undefined}
            profitPct={result.profit_pct}
            baselinePct={result.baseline_profit_pct}
          />
        </div>
      )
    }
    return (
      <div className="ml-9">
        <div className="rounded-lg border bg-muted p-3 text-xs text-muted-foreground">
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
    <div>
      <h3 className="text-sm font-semibold mb-3">Backtest Iterations</h3>
      <div className="space-y-3">
        {backtests.map((bt, i) => (
          <div
            key={bt.id}
            className={cn(
              "rounded-lg border p-3 space-y-2 hover:bg-muted/40 transition-colors",
              i === bestIdx && "border-primary/40 bg-primary/5"
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">#{i + 1}</span>
                {i === bestIdx && (
                  <span className="text-[10px] uppercase tracking-wider bg-primary/15 text-primary px-1.5 py-0.5 rounded">Best</span>
                )}
                <span>·</span>
                <span>{bt.index}</span>
                <span>·</span>
                <span>Max {bt.max_stocks}</span>
                <span>·</span>
                <span>Rebal {bt.rebalance_interval_weeks}w</span>
              </div>
              <Link to={`/backtest/${bt.id}`} className="text-xs text-primary hover:underline flex-shrink-0">
                View
              </Link>
            </div>

            <div className="text-xs">
              <span className="text-muted-foreground">Rule: </span>
              <code className="text-primary/80 bg-primary/10 px-1.5 py-0.5 rounded text-xs break-all">{bt.rule}</code>
            </div>

            {bt.sort_expr && (
              <div className="text-xs">
                <span className="text-muted-foreground">Sort: </span>
                <code className="text-primary/80 bg-primary/10 px-1.5 py-0.5 rounded text-xs break-all">{bt.sort_expr}</code>
              </div>
            )}

            <div className="grid grid-cols-5 gap-2 text-xs pt-1">
              <div>
                <div className="text-muted-foreground text-[10px] uppercase tracking-wider">Return</div>
                <div className={cn("font-semibold font-mono tabular-nums", bt.profit_pct >= 0 ? "text-positive" : "text-destructive")}>
                  {bt.profit_pct >= 0 ? "+" : ""}{bt.profit_pct.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-muted-foreground text-[10px] uppercase tracking-wider">Sharpe</div>
                <div className="font-semibold font-mono tabular-nums">{bt.scores?.sharpe_ratio.toFixed(2) ?? "—"}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-[10px] uppercase tracking-wider">Sortino</div>
                <div className="font-semibold font-mono tabular-nums">{bt.scores?.sortino_ratio.toFixed(2) ?? "—"}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-[10px] uppercase tracking-wider">Max DD</div>
                <div className="font-semibold font-mono tabular-nums text-destructive">{bt.scores?.max_drawdown_pct.toFixed(1) ?? "—"}%</div>
              </div>
              <div>
                <div className="text-muted-foreground text-[10px] uppercase tracking-wider">Win</div>
                <div className="font-semibold font-mono tabular-nums">{bt.scores ? `${(bt.scores.win_rate * 100).toFixed(0)}%` : "—"}</div>
              </div>
            </div>
          </div>
        ))}
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
          } else if (evt.event === "tool_call" && evt.data.name === "run_backtest") {
            result.push({ type: "tool_call", name: evt.data.name, input: evt.data.input })
          } else if (evt.event === "tool_result" && evt.data.name === "run_backtest") {
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

  // Continuously poll the strategy. While idle/failed, poll slowly; while running, poll fast.
  useEffect(() => {
    if (!id) return
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null

    const tick = async () => {
      try {
        const stratRes = await fetch(`/api/strategies/${id}`)
        if (!stratRes.ok) throw new Error("Strategy not found")
        const data: StrategyDetail = await stratRes.json()
        if (cancelled) return
        setStrategy(data)
        setMessages(parseStrategyMessages(data))
        setIsRunning(data.status === "running")
        setLoading(false)
        const interval = data.status === "running" ? POLL_INTERVAL_MS : POLL_INTERVAL_MS * 5
        timer = setTimeout(tick, interval)
      } catch (err) {
        if (cancelled) return
        console.error(err)
        setLoading(false)
        timer = setTimeout(tick, POLL_INTERVAL_MS * 5)
      }
    }

    tick()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [id])

  const handleFollowUp = useCallback(async () => {
    if (!followUp.trim() || isRunning || !id) return

    const userMessage = followUp.trim()
    setFollowUp("")
    setMessages((prev) => [...prev, { type: "user", content: userMessage }])
    setIsRunning(true)

    try {
      const response = await fetch(`/api/strategies/${id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction: userMessage }),
      })

      if (!response.ok) {
        const err = await response.text()
        setMessages((prev) => [...prev, { type: "error", message: `Request failed: ${err}` }])
        setIsRunning(false)
      }
    } catch (err) {
      setMessages((prev) => [...prev, { type: "error", message: `Connection error: ${err}` }])
      setIsRunning(false)
    }
  }, [followUp, isRunning, id])

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
    <div className="flex flex-col h-screen">
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
            strategy.status === "idle" && "bg-positive-bg text-positive-foreground",
            strategy.status === "running" && "bg-info-bg text-info-foreground",
            strategy.status === "failed" && "bg-negative-bg text-negative-foreground",
          )}>
            {strategy.status}
          </span>
        </div>
      </div>

      {/* Split: messages on left (50%), backtest iterations on right (50%) */}
      <div className="flex-1 flex min-h-0">
        {/* Left: messages + follow-up */}
        <div className="basis-1/2 flex flex-col border-r min-w-0">
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
              <button
                onClick={handleFollowUp}
                disabled={!followUp.trim() || isRunning}
                className={cn(
                  "flex-shrink-0 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium transition-colors self-end",
                  "hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed",
                  "flex items-center gap-2"
                )}
              >
                {isRunning ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                {isRunning ? "Running..." : "Send"}
              </button>
            </div>
          </div>
        </div>

        {/* Right: backtest iterations */}
        <div className="basis-1/2 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {strategy.backtests.length > 0 ? (
              <BacktestComparisonTable backtests={strategy.backtests} />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground/60 space-y-3">
                <p className="text-sm">No backtest iterations yet.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
