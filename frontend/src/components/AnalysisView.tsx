import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { StockTable } from "@/components/StockTable"
import type { AnalysisData } from "@/types/stock"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

function formatDate(dateStr: string): string {
  // Format: "20251021" -> "21/10/2025"
  if (dateStr.length !== 8) return dateStr
  const year = dateStr.slice(0, 4)
  const month = dateStr.slice(4, 6)
  const day = dateStr.slice(6, 8)
  return `${day}/${month}/${year}`
}

export function AnalysisView() {
  const { file: urlFile } = useParams<{ file?: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<AnalysisData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingFiles, setLoadingFiles] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [availableFiles, setAvailableFiles] = useState<string[]>([])
  const [selectedFile, setSelectedFile] = useState<string>("")

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

  // Load analysis data when selected file changes
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

    fetch(`/api/analysis/${selectedFile}`)
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
  }, [selectedFile])

  if (loadingFiles) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground">Loading analysis files...</p>
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
            Make sure the API server is running and analysis files are available
          </p>
        </div>
      </div>
    )
  }

  const now = new Date()
  const generatedDate = `${String(now.getDate()).padStart(2, "0")}/${String(now.getMonth() + 1).padStart(2, "0")}/${now.getFullYear()}`

  return (
    <div className="relative mx-auto max-w-[2000px] px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="mb-8 text-center">
          <h1 className="mb-4 bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-4xl font-bold tracking-tight text-transparent sm:text-5xl">
            Stock Analysis Report
          </h1>
          <div className="mb-4 flex items-center justify-center gap-4">
            <label htmlFor="file-select" className="text-sm font-medium text-muted-foreground">
              Select Analysis:
            </label>
            <Select value={selectedFile} onValueChange={(value) => {
              setSelectedFile(value)
              navigate(`/analysis/${value}`)
            }}>
              <SelectTrigger id="file-select" className="w-[250px]">
                <SelectValue placeholder="Select an analysis file" />
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
              Analysis Date: {formatDate(data.analysis_date)} • Generated on{" "}
              {generatedDate} • {data.data.length} stocks analyzed • 52-week metrics
            </p>
          )}
        </header>

        {/* Main Table */}
        <main>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="flex flex-col items-center gap-4">
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                <p className="text-muted-foreground">Loading analysis data...</p>
              </div>
            </div>
          ) : error ? (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
              <h2 className="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h2>
              <p className="text-muted-foreground">{error}</p>
            </div>
          ) : data ? (
            <StockTable data={data.data} />
          ) : null}
        </main>

        {/* Footer */}
        <footer className="mt-8 text-center text-sm text-muted-foreground">
          <p>Click column headers to sort • Add filters above the table</p>
        </footer>
      </div>
  )
}
