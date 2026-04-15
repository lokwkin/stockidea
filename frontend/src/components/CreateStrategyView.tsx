import { useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Bot, Send } from "lucide-react"
import { cn } from "@/lib/utils"

const MODEL_OPTIONS = [
  { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
  { value: "claude-opus-4-20250514", label: "Claude Opus 4" },
  { value: "gpt-5.4", label: "GPT-5.4" },
]

export function CreateStrategyView() {
  const navigate = useNavigate()
  const [instruction, setInstruction] = useState("")
  const [model, setModel] = useState(MODEL_OPTIONS[0].value)
  const [dateStart, setDateStart] = useState("")
  const [dateEnd, setDateEnd] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = useCallback(async () => {
    if (!instruction.trim() || isSubmitting) return

    setIsSubmitting(true)

    try {
      const body: Record<string, string> = {
        instruction: instruction.trim(),
        model,
      }
      if (dateStart) body.date_start = dateStart
      if (dateEnd) body.date_end = dateEnd

      const response = await fetch("/api/strategies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const err = await response.text()
        console.error("Failed to create strategy:", err)
        setIsSubmitting(false)
        return
      }

      // Read the SSE stream to get the strategy_id from the first event
      const reader = response.body?.getReader()
      if (!reader) {
        setIsSubmitting(false)
        return
      }

      const decoder = new TextDecoder()
      let buffer = ""

      // Read until we get the strategy_created event
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
            if (currentEvent === "strategy_created") {
              const parsed = JSON.parse(currentData)
              // Cancel the reader — the StrategyView will reconnect
              reader.cancel()
              navigate(`/strategy/${parsed.strategy_id}`)
              return
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
      console.error("Error creating strategy:", err)
    } finally {
      setIsSubmitting(false)
    }
  }, [instruction, model, dateStart, dateEnd, isSubmitting, navigate])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && e.altKey) {
        e.preventDefault()
        handleSubmit()
      }
    },
    [handleSubmit]
  )

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      <div className="flex-shrink-0 border-b px-6 py-4">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
          <Bot className="h-7 w-7 text-primary" />
          New Strategy
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Describe your strategy idea and the AI agent will design, backtest, and iterate to find the best rule.
        </p>
      </div>

      <div className="flex-1 flex flex-col justify-center px-6 py-8 space-y-6">
        {/* Instruction */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">Strategy Idea</label>
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. I want a momentum strategy that avoids volatile stocks and big drawdowns..."
            className={cn(
              "w-full rounded-lg border bg-background px-4 py-3 text-sm resize-none",
              "placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30",
              "min-h-[100px]"
            )}
            disabled={isSubmitting}
            rows={4}
          />
        </div>

        {/* Model */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">Model</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full rounded-lg border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            disabled={isSubmitting}
          >
            {MODEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date Range */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              Start Date <span className="text-muted-foreground font-normal">(optional, default: 3 years ago)</span>
            </label>
            <input
              type="date"
              value={dateStart}
              onChange={(e) => setDateStart(e.target.value)}
              className="w-full rounded-lg border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              disabled={isSubmitting}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              End Date <span className="text-muted-foreground font-normal">(optional, default: today)</span>
            </label>
            <input
              type="date"
              value={dateEnd}
              onChange={(e) => setDateEnd(e.target.value)}
              className="w-full rounded-lg border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              disabled={isSubmitting}
            />
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!instruction.trim() || isSubmitting}
          className={cn(
            "w-full rounded-lg bg-primary text-primary-foreground px-4 py-3 text-sm font-medium transition-colors",
            "hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed",
            "flex items-center justify-center gap-2"
          )}
        >
          <Send className="h-4 w-4" />
          {isSubmitting ? "Starting..." : "Start Strategy"}
        </button>
      </div>
    </div>
  )
}
