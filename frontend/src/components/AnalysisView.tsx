import { useEffect, useState, useCallback, useMemo, useRef } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import { StockTable } from "@/components/StockTable"
import type { AnalysisData } from "@/types/stock"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { dateFormat } from "@/lib/utils"

export function AnalysisView() {
  const { file: urlFile } = useParams<{ file?: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [data, setData] = useState<AnalysisData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingFiles, setLoadingFiles] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [availableFiles, setAvailableFiles] = useState<string[]>([])
  const [selectedFile, setSelectedFile] = useState<string>("")
  const [rule, setRule] = useState<string>("")
  const tableRef = useRef<HTMLDivElement>(null)
  
  const targetSymbol = searchParams.get("symbol")
  const urlRule = searchParams.get("rule")

  // Load available files on mount
  useEffect(() => {
    fetch("/api/analysis")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load analysis list")
        return res.json()
      })
      .then((files: string[]) => {
        if (files.length === 0) {
          throw new Error("No analysis files available")
        }
        setAvailableFiles(files)
        // Use URL file if provided and valid, otherwise use the most recent file
        if (urlFile && files.includes(urlFile)) {
          setSelectedFile(urlFile)
        } else {
          setSelectedFile(files[0])
          // Update URL if no file in URL or invalid file
          if (!urlFile || !files.includes(urlFile)) {
            navigate(`/analysis/${files[0]}`, { replace: true })
          }
        }
        setLoadingFiles(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoadingFiles(false)
      })
  }, [])

  // Handle URL file changes
  useEffect(() => {
    if (urlFile && availableFiles.includes(urlFile) && selectedFile !== urlFile) {
      setSelectedFile(urlFile)
    }
  }, [urlFile, availableFiles, selectedFile])

  // Set rule from URL query param on mount
  useEffect(() => {
    if (urlRule) {
      setRule(urlRule)
    }
  }, [urlRule])

  // Load analysis data when selected file or rule changes
  useEffect(() => {
    if (!selectedFile) return

    let cancelled = false

    // Start loading - use requestAnimationFrame to avoid synchronous setState warning
    requestAnimationFrame(() => {
      if (!cancelled) {
        setLoading(true)
        setError(null)
      }
    })

    const url = rule.trim()
      ? `/api/analysis/${selectedFile}?rule=${encodeURIComponent(rule.trim())}`
      : `/api/analysis/${selectedFile}`

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load analysis data")
        return res.json()
      })
      .then((json: AnalysisData) => {
        if (!cancelled) {
          setData(json)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message)
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedFile, rule])

  // Scroll to target symbol when data loads
  useEffect(() => {
    if (!targetSymbol || !data || loading) return

    // Wait for table to render, then scroll to the symbol
    const timer = setTimeout(() => {
      if (tableRef.current) {
        const row = tableRef.current.querySelector(`[data-symbol="${targetSymbol}"]`) as HTMLElement
        if (row) {
          row.scrollIntoView({ behavior: "smooth", block: "center" })
          // Highlight the row temporarily
          row.classList.add("bg-primary/10")
          setTimeout(() => {
            row.classList.remove("bg-primary/10")
          }, 2000)
        }
      }
    }, 100)

    return () => clearTimeout(timer)
  }, [targetSymbol, data, loading])

  const handleRuleSubmit = useCallback(() => {
    if (!selectedFile) return

    setLoading(true)
    setError(null)

    const url = rule.trim()
      ? `/api/analysis/${selectedFile}?rule=${encodeURIComponent(rule.trim())}`
      : `/api/analysis/${selectedFile}`

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load analysis data")
        return res.json()
      })
      .then((json: AnalysisData) => {
        setData(json)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [selectedFile, rule])

  const generatedDate = useMemo(() => {
    return dateFormat(new Date())
  }, [])

  if (loadingFiles) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground">Loading trend data files...</p>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
          <h2 className="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h2>
          <p className="text-muted-foreground">{error ?? "No data available"}</p>
          <p className="mt-4 text-sm text-muted-foreground">
            Make sure the API server is running and trend data files are available
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative mx-auto max-w-[2000px] px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="mb-8 text-center">
          <h1 className="mb-4 bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
            Stock Trend Data
          </h1>
          <div className="mb-4 flex items-center justify-center gap-4">
            <label htmlFor="file-select" className="text-sm font-medium text-muted-foreground">
              Select Trend Data:
            </label>
            <Select value={selectedFile} onValueChange={(value) => {
              setSelectedFile(value)
              const symbolParam = targetSymbol ? `?symbol=${targetSymbol}` : ""
              navigate(`/analysis/${value}${symbolParam}`)
            }}>
              <SelectTrigger id="file-select" className="w-[250px]">
                <SelectValue placeholder="Select a trend data file" />
              </SelectTrigger>
              <SelectContent>
                {availableFiles.map((file) => (
                  <SelectItem key={file} value={file}>
                    {file}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {data && (
            <p className="text-sm text-muted-foreground">
              Trend Data Date: {dateFormat(data.analysis_date)} • Generated on{" "}
              {generatedDate} • {data.data.length} stocks analyzed • 52-week metrics
            </p>
          )}
        </header>

        {/* Rule Input Section */}
        <div className="mb-6 flex flex-col items-center gap-4">
          <div className="w-full max-w-2xl">
            <label htmlFor="rule-input" className="text-sm font-medium text-muted-foreground mb-1 block">
              Rule (optional):
            </label>
            <div className="flex gap-2 items-start">
              <textarea
                id="rule-input"
                value={rule}
                onChange={(e) => setRule(e.target.value)}
                placeholder="Enter rule expression (e.g., change_3m_pct > 10 AND max_drop_2w_pct > 15)"
                className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
                rows={3}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault()
                    handleRuleSubmit()
                  }
                }}
              />
              <Button
                type="button"
                onClick={handleRuleSubmit}
                className="shrink-0"
                disabled={loading}
              >
                Apply Rule
              </Button>
            </div>
          </div>
        </div>

        {/* Main Table */}
        <main>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="flex flex-col items-center gap-4">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                <p className="text-muted-foreground">Loading trend data...</p>
              </div>
            </div>
          ) : error ? (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
              <h2 className="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h2>
              <p className="text-muted-foreground">{error}</p>
            </div>
          ) : data ? (
            <div ref={tableRef}>
              <StockTable data={data.data} highlightedSymbol={targetSymbol || undefined} />
            </div>
          ) : null}
        </main>

        {/* Footer */}
        <footer className="mt-8 text-center text-sm text-muted-foreground">
          <p>Click column headers to sort</p>
        </footer>
      </div>
  )
}
