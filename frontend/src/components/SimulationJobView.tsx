import { useEffect, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { SimulationJob } from "@/types/simulation"

const POLL_INTERVAL_MS = 2000

function StatusBadge({ status }: { status: SimulationJob["status"] }) {
  const styles: Record<SimulationJob["status"], string> = {
    pending: "bg-yellow-100 text-yellow-800 border-yellow-300",
    running: "bg-blue-100 text-blue-800 border-blue-300",
    completed: "bg-green-100 text-green-800 border-green-300",
    failed: "bg-red-100 text-red-800 border-red-300",
  }
  const labels: Record<SimulationJob["status"], string> = {
    pending: "Pending",
    running: "Running",
    completed: "Completed",
    failed: "Failed",
  }
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-medium ${styles[status]}`}>
      {(status === "pending" || status === "running") && (
        <span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-current" />
      )}
      {labels[status]}
    </span>
  )
}

export function SimulationJobView() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const [job, setJob] = useState<SimulationJob | null>(null)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchJob = async () => {
    if (!jobId) return
    try {
      const res = await fetch(`/api/jobs/${jobId}`)
      if (!res.ok) {
        setError(`Failed to fetch job status (${res.status})`)
        return
      }
      const data: SimulationJob = await res.json()
      setJob(data)

      if (data.status === "completed" && data.simulation_id) {
        clearInterval(intervalRef.current!)
        navigate(`/simulation/${data.simulation_id}`)
      } else if (data.status === "failed") {
        clearInterval(intervalRef.current!)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error")
    }
  }

  useEffect(() => {
    fetchJob()
    intervalRef.current = setInterval(fetchJob, POLL_INTERVAL_MS)
    return () => clearInterval(intervalRef.current!)
  }, [jobId])

  return (
    <div className="mx-auto max-w-2xl px-4 py-16 sm:px-6 lg:px-8">
      <header className="mb-10 text-center">
        <h1 className="mb-2 bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-4xl font-bold tracking-tight text-transparent">
          Simulation Running
        </h1>
        <p className="text-muted-foreground">Your simulation has been queued and will run shortly.</p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm font-medium text-destructive">{error}</p>
        </div>
      )}

      {job && (
        <div className="rounded-lg border bg-card p-8 space-y-6 text-center">
          <div className="flex justify-center">
            <StatusBadge status={job.status} />
          </div>

          {(job.status === "pending" || job.status === "running") && (
            <div className="flex justify-center">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-muted border-t-primary" />
            </div>
          )}

          {job.status === "pending" && (
            <p className="text-muted-foreground text-sm">Waiting for the worker to pick up this job…</p>
          )}

          {job.status === "running" && (
            <p className="text-muted-foreground text-sm">Simulation is running. This may take a minute.</p>
          )}

          {job.status === "failed" && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-left">
              <p className="text-sm font-medium text-destructive mb-1">Simulation failed</p>
              <p className="text-xs text-destructive/80 font-mono whitespace-pre-wrap">
                {job.error_message ?? "Unknown error"}
              </p>
            </div>
          )}

          <div className="border-t pt-4 text-xs text-muted-foreground space-y-1 text-left">
            <div className="flex justify-between">
              <span>Job ID</span>
              <span className="font-mono">{job.id}</span>
            </div>
            {job.started_at && (
              <div className="flex justify-between">
                <span>Started</span>
                <span>{new Date(job.started_at).toLocaleTimeString()}</span>
              </div>
            )}
          </div>

          {job.status === "failed" && (
            <button
              onClick={() => navigate("/simulation/create")}
              className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Try Again
            </button>
          )}
        </div>
      )}

      {!job && !error && (
        <div className="flex justify-center py-12">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-muted border-t-primary" />
        </div>
      )}
    </div>
  )
}
