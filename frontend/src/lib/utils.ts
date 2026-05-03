import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import dayjs from "dayjs"
import customParseFormat from "dayjs/plugin/customParseFormat"
import relativeTime from "dayjs/plugin/relativeTime"

dayjs.extend(customParseFormat)
dayjs.extend(relativeTime)

export function relativeTimeShort(dateInput: string | Date): string {
  const d = dayjs(dateInput)
  if (!d.isValid()) return ""
  const now = dayjs()
  const diffSec = now.diff(d, "second")
  if (diffSec < 60) return `${diffSec}s ago`
  const diffMin = now.diff(d, "minute")
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = now.diff(d, "hour")
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = now.diff(d, "day")
  if (diffDay < 30) return `${diffDay}d ago`
  const diffMo = now.diff(d, "month")
  if (diffMo < 12) return `${diffMo}mo ago`
  const diffYr = now.diff(d, "year")
  return `${diffYr}y ago`
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Unified date formatting function.
 * Formats dates to yyyy/mm/dd format.
 * Handles various input formats:
 * - ISO date strings (yyyy-mm-dd)
 * - 8-digit date strings (yyyyMMdd)
 * - Date objects
 * - Already formatted dates (yyyy/mm/dd) - passes through
 */
export function dateFormat(dateInput: string | Date): string {
  if (!dateInput) return ""
  
  // Handle already formatted dates (yyyy/mm/dd) - passes through
  if (typeof dateInput === "string" && /^\d{4}\/\d{2}\/\d{2}$/.test(dateInput)) {
    return dateInput
  }
  
  let date: dayjs.Dayjs | null = null
  
  if (dateInput instanceof Date) {
    date = dayjs(dateInput)
  } else if (typeof dateInput === "string") {
    // Handle 8-digit format (yyyyMMdd)
    if (dateInput.length === 8 && /^\d{8}$/.test(dateInput)) {
      date = dayjs(dateInput, "YYYYMMDD", true)
    } else {
      // Handle ISO format (yyyy-mm-dd) or other date strings
      date = dayjs(dateInput)
    }
  }
  
  // Check if date is valid
  if (!date || !date.isValid()) {
    return ""
  }
  
  return date.format("YYYY/MM/DD")
}
