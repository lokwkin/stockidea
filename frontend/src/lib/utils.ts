import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import dayjs from "dayjs"
import customParseFormat from "dayjs/plugin/customParseFormat"

dayjs.extend(customParseFormat)

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
