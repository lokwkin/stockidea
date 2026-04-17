import { useState, useEffect, useMemo, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import { Search, Loader2, ExternalLink } from "lucide-react"
import { Link } from "react-router-dom"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { StockIndicators, StockProfileResponse } from "@/types/stock"
import { COLUMNS } from "@/config/columns"

interface DailyPrice {
  symbol: string
  date: string
  adj_close: number
  volume: number | null
}

interface WeeklyPoint {
  weekEnding: string
  close: number
  volume: number
  date: string // raw ISO for API calls
}

const PERIOD_OPTIONS = [
  { label: "1Y", weeks: 52 },
  { label: "2Y", weeks: 104 },
  { label: "3Y", weeks: 156 },
  { label: "5Y", weeks: 260 },
]

/** Aggregate daily prices into weekly (Friday close) */
function aggregateWeekly(dailyPrices: DailyPrice[]): WeeklyPoint[] {
  if (!dailyPrices.length) return []

  const sorted = [...dailyPrices].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  )

  const weeks: Map<string, { close: number; volume: number; date: string }> = new Map()

  for (const p of sorted) {
    const d = new Date(p.date)
    const day = d.getUTCDay()
    const diff = (5 - day + 7) % 7
    const friday = new Date(d)
    friday.setUTCDate(friday.getUTCDate() + diff)
    const key = friday.toISOString().slice(0, 10)

    const existing = weeks.get(key)
    const vol = (existing?.volume ?? 0) + (p.volume ?? 0)
    weeks.set(key, { close: p.adj_close, volume: vol, date: p.date })
  }

  return Array.from(weeks.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([weekEnding, data]) => ({
      weekEnding,
      close: data.close,
      volume: data.volume,
      date: data.date,
    }))
}

function formatDate(d: string) {
  return d.replace(/-/g, "/")
}

function formatCurrency(v: number) {
  return `$${v.toFixed(2)}`
}

function formatVolume(v: number) {
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
  return String(v)
}

function formatMarketCap(v: number) {
  if (v >= 1_000_000_000_000) return `$${(v / 1_000_000_000_000).toFixed(2)}T`
  if (v >= 1_000_000_000) return `$${(v / 1_000_000_000).toFixed(2)}B`
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  return `$${v.toFixed(0)}`
}

/** Indicator fields to show */
const INDICATOR_DISPLAY_KEYS = [
  "change_1w_pct",
  "change_4w_pct",
  "change_13w_pct",
  "change_26w_pct",
  "change_1y_pct",
  "linear_slope_pct",
  "linear_r_squared",
  "weekly_return_std",
  "max_drawdown_pct",
  "pct_from_4w_high",
  "r_squared_13w",
  "acceleration_13w",
]

function formatIndicatorValue(key: string, val: number): { formatted: string; colorClass: string } {
  const col = COLUMNS.find((c) => c.key === key)
  let formatted: string
  let colorClass = ""

  if (col?.type === "percent") {
    const sign = val > 0 ? "+" : ""
    formatted = `${sign}${val.toFixed(2)}%`
    colorClass = val > 0 ? "text-positive" : val < 0 ? "text-destructive" : ""
  } else if (col?.type === "r_squared") {
    formatted = val.toFixed(3)
    colorClass = val >= 0.7 ? "text-positive" : val < 0.4 ? "text-destructive" : ""
  } else {
    formatted = val.toFixed(col?.decimals ?? 2)
  }

  return { formatted, colorClass }
}

function IndicatorRow({
  label,
  currentVal,
  selectedVal,
  showSelected,
}: {
  label: string
  currentVal?: { formatted: string; colorClass: string }
  selectedVal?: { formatted: string; colorClass: string }
  showSelected: boolean
}) {
  return (
    <tr className="text-sm">
      <td className="py-0.5 pr-2 text-muted-foreground">{label}</td>
      {showSelected && (
        <td className="py-0.5 px-2 text-right font-mono text-xs">
          {selectedVal ? (
            <span className={selectedVal.colorClass}>{selectedVal.formatted}</span>
          ) : (
            <span className="text-muted-foreground/30">—</span>
          )}
        </td>
      )}
      <td className="py-0.5 pl-2 text-right font-mono text-sm">
        {currentVal ? (
          <span className={currentVal.colorClass}>{currentVal.formatted}</span>
        ) : (
          <span className="text-muted-foreground/30">—</span>
        )}
      </td>
    </tr>
  )
}

function ChartTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const data = payload[0]?.payload as WeeklyPoint | undefined
  if (!data) return null

  return (
    <div className="rounded-md border bg-card px-3 py-2 shadow-sm text-sm">
      <div className="font-medium mb-1">{formatDate(data.weekEnding)}</div>
      <div>Close: <span className="font-medium">{formatCurrency(data.close)}</span></div>
      {data.volume > 0 && (
        <div>Volume: <span className="font-medium">{formatVolume(data.volume)}</span></div>
      )}
    </div>
  )
}

export function StockChartView() {
  const { symbol: urlSymbol } = useParams<{ symbol?: string }>()
  const navigate = useNavigate()
  const [searchInput, setSearchInput] = useState(urlSymbol?.toUpperCase() || "")
  const [symbol, setSymbol] = useState(urlSymbol?.toUpperCase() || "")
  const [prices, setPrices] = useState<DailyPrice[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [periodWeeks, setPeriodWeeks] = useState(156) // default 3Y

  // Current (latest) indicators
  const [currentIndicators, setCurrentIndicators] = useState<StockIndicators | null>(null)
  const [currentIndicatorsDate, setCurrentIndicatorsDate] = useState<string | null>(null)
  const [loadingCurrent, setLoadingCurrent] = useState(false)

  // Selected date indicators
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [selectedIndicators, setSelectedIndicators] = useState<StockIndicators | null>(null)
  const [loadingSelected, setLoadingSelected] = useState(false)

  // FMP company profile + peers
  const [profileData, setProfileData] = useState<StockProfileResponse | null>(null)
  const [loadingProfile, setLoadingProfile] = useState(false)
  const [descExpanded, setDescExpanded] = useState(false)

  // Compute from/to dates based on period
  const getFromDate = useCallback((weeks: number) => {
    const d = new Date()
    d.setDate(d.getDate() - weeks * 7)
    return d.toISOString().slice(0, 10)
  }, [])

  // Fetch price data
  const fetchPrices = useCallback(async (sym: string, weeks: number) => {
    if (!sym) return
    setLoading(true)
    setError(null)
    setSelectedDate(null)
    setSelectedIndicators(null)

    try {
      const fromDate = getFromDate(weeks)
      const res = await fetch(`/api/stocks/${sym}/prices?from=${fromDate}`)
      if (!res.ok) throw new Error(`Failed to load prices for ${sym}`)
      const data: DailyPrice[] = await res.json()
      setPrices(data)
      setSymbol(sym)
    } catch (e) {
      setError((e as Error).message)
      setPrices([])
    } finally {
      setLoading(false)
    }
  }, [getFromDate])

  // Fetch company profile + peers (live from FMP via backend)
  const fetchProfile = useCallback(async (sym: string) => {
    if (!sym) return
    setLoadingProfile(true)
    setProfileData(null)
    setDescExpanded(false)
    try {
      const res = await fetch(`/api/stocks/${sym}/profile`)
      if (!res.ok) {
        setLoadingProfile(false)
        return
      }
      const json: StockProfileResponse = await res.json()
      setProfileData(json)
    } catch {
      setProfileData(null)
    } finally {
      setLoadingProfile(false)
    }
  }, [])

  // Fetch latest indicators for symbol
  const fetchCurrentIndicators = useCallback(async (sym: string) => {
    if (!sym) return
    setLoadingCurrent(true)
    setCurrentIndicators(null)
    setCurrentIndicatorsDate(null)

    try {
      const res = await fetch(`/api/indicators/symbol/${sym}/latest`)
      if (!res.ok) {
        setLoadingCurrent(false)
        return
      }
      const json = await res.json()
      if (json.data) {
        setCurrentIndicators(json.data as StockIndicators)
        setCurrentIndicatorsDate(json.date)
      }
    } catch {
      setCurrentIndicators(null)
    } finally {
      setLoadingCurrent(false)
    }
  }, [])

  // Load from URL on mount
  useEffect(() => {
    if (urlSymbol) {
      const sym = urlSymbol.toUpperCase()
      setSearchInput(sym)
      fetchPrices(sym, periodWeeks)
      fetchCurrentIndicators(sym)
      fetchProfile(sym)
    }
  }, [urlSymbol, fetchPrices, fetchCurrentIndicators, fetchProfile, periodWeeks])

  const handleSearch = useCallback(() => {
    const sym = searchInput.trim().toUpperCase()
    if (!sym) return
    navigate(`/chart/${sym}`)
  }, [searchInput, navigate])

  const handlePeriodChange = useCallback((weeks: number) => {
    setPeriodWeeks(weeks)
    if (symbol) {
      fetchPrices(symbol, weeks)
    }
  }, [symbol, fetchPrices])

  const weeklyData = useMemo(() => aggregateWeekly(prices), [prices])

  // Price domain for Y-axis
  const priceDomain = useMemo(() => {
    if (!weeklyData.length) return [0, 100]
    const prices = weeklyData.map((d) => d.close)
    const min = Math.min(...prices)
    const max = Math.max(...prices)
    const padding = (max - min) * 0.05
    return [Math.floor(min - padding), Math.ceil(max + padding)]
  }, [weeklyData])

  // Handle click on chart point → load indicators for selected date
  const handleChartClick = useCallback(
    async (state: any) => {
      // Recharts v3: state has activeTooltipIndex / activeLabel instead of activePayload
      const index = state?.activeTooltipIndex
      if (index == null || index < 0 || index >= weeklyData.length) return
      const point = weeklyData[index]
      const indicatorDate = point.weekEnding

      setSelectedDate(indicatorDate)
      setLoadingSelected(true)
      setSelectedIndicators(null)

      try {
        const res = await fetch(`/api/indicators/symbol/${symbol}/${indicatorDate}`)
        if (!res.ok) {
          setSelectedIndicators(null)
          setLoadingSelected(false)
          return
        }
        const json = await res.json()
        setSelectedIndicators(json.data as StockIndicators | null)
      } catch {
        setSelectedIndicators(null)
      } finally {
        setLoadingSelected(false)
      }
    },
    [symbol, weeklyData]
  )

  const hasIndicators = currentIndicators || selectedIndicators
  const showPanel = !loading && symbol

  return (
    <div className="flex h-screen">
      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex-shrink-0 px-6 pt-8 pb-6 border-b">
          <div className="mb-6">
            <h1 className="mb-2 text-3xl font-semibold tracking-tight text-foreground">
              Stocks
            </h1>
            <p className="text-muted-foreground">
              Weekly price history with click-to-inspect indicator analysis
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative w-64">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <Input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value.toUpperCase())}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSearch()
                }}
                placeholder="Enter symbol (e.g. AAPL)"
                className="pl-8 font-mono uppercase"
              />
            </div>
            <Button onClick={handleSearch}>Search</Button>

            {symbol && !loading && (
              <span className="ml-2 text-lg font-semibold text-foreground">{symbol}</span>
            )}

            {/* Period selector */}
            {symbol && !loading && (
              <div className="flex items-center gap-1 ml-auto">
                {PERIOD_OPTIONS.map((opt) => (
                  <button
                    key={opt.label}
                    onClick={() => handlePeriodChange(opt.weeks)}
                    className={cn(
                      "h-9 px-3 rounded-md text-sm font-medium transition-colors",
                      periodWeeks === opt.weeks
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted"
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </header>

        {/* Chart area */}
        <div className="flex-1 overflow-auto px-6 py-4">
          {!symbol && !loading && (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Enter a stock symbol to view its chart
            </div>
          )}

          {loading && (
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-3 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
                Loading prices...
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center h-full">
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
                <p className="text-destructive font-medium">{error}</p>
              </div>
            </div>
          )}

          {!loading && !error && weeklyData.length > 0 && (
            <div className="space-y-2">
              {/* Company profile + peers — shown above the chart */}
              {(loadingProfile || profileData) && (
                <div className="rounded-lg border bg-card p-5 space-y-4 mb-4">
                  {loadingProfile && !profileData && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading company profile...
                    </div>
                  )}

                  {profileData?.profile && (
                    <>
                      {/* Header: name + sector chips */}
                      <div className="flex items-start gap-4">
                        {profileData.profile.image && (
                          <img
                            src={profileData.profile.image}
                            alt={profileData.profile.companyName ?? symbol}
                            className="w-12 h-12 rounded border bg-background object-contain"
                            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none" }}
                          />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h2 className="text-xl font-semibold">
                              {profileData.profile.companyName ?? symbol}
                            </h2>
                            <span className="text-sm text-muted-foreground font-mono">{symbol}</span>
                          </div>
                          <div className="flex items-center gap-2 mt-1.5 flex-wrap text-xs">
                            {profileData.profile.sector && (
                              <span className="bg-muted px-2 py-0.5 rounded">{profileData.profile.sector}</span>
                            )}
                            {profileData.profile.industry && (
                              <span className="bg-muted px-2 py-0.5 rounded">{profileData.profile.industry}</span>
                            )}
                            {profileData.profile.exchangeShortName && (
                              <span className="text-muted-foreground">{profileData.profile.exchangeShortName}</span>
                            )}
                            {profileData.profile.country && (
                              <span className="text-muted-foreground">· {profileData.profile.country}</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Key facts grid */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs pt-2 border-t">
                        {profileData.profile.mktCap !== undefined && (
                          <div>
                            <div className="text-muted-foreground uppercase tracking-wide">Market Cap</div>
                            <div className="font-semibold font-mono tabular-nums">{formatMarketCap(profileData.profile.mktCap)}</div>
                          </div>
                        )}
                        {profileData.profile.beta !== undefined && (
                          <div>
                            <div className="text-muted-foreground uppercase tracking-wide">Beta</div>
                            <div className="font-semibold font-mono tabular-nums">{profileData.profile.beta.toFixed(2)}</div>
                          </div>
                        )}
                        {profileData.profile.fullTimeEmployees && (
                          <div>
                            <div className="text-muted-foreground uppercase tracking-wide">Employees</div>
                            <div className="font-semibold font-mono tabular-nums">{Number(profileData.profile.fullTimeEmployees).toLocaleString()}</div>
                          </div>
                        )}
                        {profileData.profile.ipoDate && (
                          <div>
                            <div className="text-muted-foreground uppercase tracking-wide">IPO Date</div>
                            <div className="font-semibold font-mono tabular-nums">{profileData.profile.ipoDate}</div>
                          </div>
                        )}
                        {profileData.profile.ceo && (
                          <div>
                            <div className="text-muted-foreground uppercase tracking-wide">CEO</div>
                            <div className="font-semibold">{profileData.profile.ceo}</div>
                          </div>
                        )}
                        {profileData.profile.website && (
                          <div>
                            <div className="text-muted-foreground uppercase tracking-wide">Website</div>
                            <a
                              href={profileData.profile.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-semibold text-primary hover:underline inline-flex items-center gap-1"
                            >
                              Visit <ExternalLink className="h-3 w-3" />
                            </a>
                          </div>
                        )}
                      </div>

                      {/* Description */}
                      {profileData.profile.description && (
                        <div className="pt-2 border-t">
                          <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1.5">About</div>
                          <p className={cn(
                            "text-sm text-foreground/90 leading-relaxed",
                            !descExpanded && "line-clamp-4"
                          )}>
                            {profileData.profile.description}
                          </p>
                          {profileData.profile.description.length > 280 && (
                            <button
                              onClick={() => setDescExpanded((v) => !v)}
                              className="text-xs text-primary hover:underline mt-1"
                            >
                              {descExpanded ? "Show less" : "Show more"}
                            </button>
                          )}
                        </div>
                      )}
                    </>
                  )}

                  {/* Peers */}
                  {profileData && profileData.peers.length > 0 && (
                    <div className="pt-2 border-t">
                      <div className="text-xs text-muted-foreground uppercase tracking-wide mb-2">Peers</div>
                      <div className="flex flex-wrap gap-2">
                        {profileData.peers.map((peer) => (
                          <Link
                            key={peer}
                            to={`/chart/${peer}`}
                            className="text-xs font-mono px-2 py-1 rounded border hover:bg-muted hover:border-primary/50 transition-colors"
                          >
                            {peer}
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="text-xs text-muted-foreground">
                {weeklyData.length} weeks &middot; {formatDate(weeklyData[0].weekEnding)} to{" "}
                {formatDate(weeklyData[weeklyData.length - 1].weekEnding)}
                {selectedDate && (
                  <span className="ml-2">
                    &middot; Selected: <span className="font-medium text-foreground">{formatDate(selectedDate)}</span>
                  </span>
                )}
              </div>

              {/* Price chart */}
              <div className="h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={weeklyData}
                    onClick={handleChartClick}
                    margin={{ top: 5, right: 20, bottom: 5, left: 10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis
                      dataKey="weekEnding"
                      tickFormatter={(v) => v.slice(5)} // MM-DD
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      interval="preserveStartEnd"
                      minTickGap={60}
                    />
                    <YAxis
                      domain={priceDomain}
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      tickFormatter={(v) => `$${v}`}
                      width={60}
                    />
                    <Tooltip content={<ChartTooltip />} />

                    {selectedDate && (
                      <ReferenceLine
                        x={selectedDate}
                        stroke="hsl(var(--primary))"
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                      />
                    )}

                    <Line
                      type="monotone"
                      dataKey="close"
                      stroke="hsl(var(--primary))"
                      strokeWidth={1.5}
                      dot={false}
                      activeDot={{ r: 4, fill: "hsl(var(--primary))" }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* Volume chart */}
              <div className="h-[120px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={weeklyData}
                    onClick={handleChartClick}
                    margin={{ top: 5, right: 20, bottom: 5, left: 10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis
                      dataKey="weekEnding"
                      tickFormatter={(v) => v.slice(5)}
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      interval="preserveStartEnd"
                      minTickGap={60}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      tickFormatter={formatVolume}
                      width={60}
                    />

                    {selectedDate && (
                      <ReferenceLine
                        x={selectedDate}
                        stroke="hsl(var(--primary))"
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                      />
                    )}

                    <Bar
                      dataKey="volume"
                      fill="hsl(var(--muted-foreground))"
                      opacity={0.3}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

            </div>
          )}
        </div>
      </div>

      {/* Indicators side panel — always show when symbol is loaded */}
      {showPanel && (
        <div className="w-80 border-l bg-background overflow-y-auto flex-shrink-0">
          <div className="sticky top-0 bg-background border-b px-4 py-3">
            <div className="text-sm font-semibold">{symbol} Indicators</div>
            {selectedDate && currentIndicatorsDate && (
              <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="inline-block w-2 h-2 rounded-full bg-muted-foreground/40" />
                  Selected: {formatDate(selectedDate)}
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block w-2 h-2 rounded-full bg-foreground" />
                  Latest: {formatDate(currentIndicatorsDate)}
                </span>
              </div>
            )}
            {!selectedDate && currentIndicatorsDate && (
              <div className="text-xs text-muted-foreground mt-1">
                As of {formatDate(currentIndicatorsDate)}
              </div>
            )}
          </div>

          <div className="px-4 py-3">
            {(loadingCurrent || loadingSelected) && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading indicators...
              </div>
            )}

            {!loadingCurrent && !loadingSelected && !hasIndicators && (
              <p className="text-sm text-muted-foreground py-4">
                No indicator data available.
              </p>
            )}

            {!loadingCurrent && !loadingSelected && hasIndicators && (
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-muted-foreground border-b">
                    <th className="py-1.5 pr-2 text-left font-medium">Metric</th>
                    {selectedDate && (
                      <th className="py-1.5 px-2 text-right font-medium">Selected</th>
                    )}
                    <th className="py-1.5 pl-2 text-right font-medium">Latest</th>
                  </tr>
                </thead>
                <tbody>
                  {INDICATOR_DISPLAY_KEYS.map((key) => {
                    const col = COLUMNS.find((c) => c.key === key)
                    const label = col?.displayName || key

                    const currentRaw = currentIndicators?.[key as keyof StockIndicators]
                    const selectedRaw = selectedIndicators?.[key as keyof StockIndicators]

                    if (currentRaw === undefined && selectedRaw === undefined) return null

                    const currentVal = typeof currentRaw === "number"
                      ? formatIndicatorValue(key, currentRaw)
                      : undefined

                    const selectedVal = typeof selectedRaw === "number" && selectedDate
                      ? formatIndicatorValue(key, selectedRaw)
                      : undefined

                    return (
                      <IndicatorRow
                        key={key}
                        label={label}
                        currentVal={currentVal}
                        selectedVal={selectedVal}
                        showSelected={!!selectedDate}
                      />
                    )
                  })}
                </tbody>
              </table>
            )}

            {selectedDate && (
              <button
                onClick={() => {
                  setSelectedDate(null)
                  setSelectedIndicators(null)
                }}
                className="mt-4 w-full text-sm text-muted-foreground hover:text-foreground transition-colors py-1.5 border rounded-md"
              >
                Clear selection
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
