export function formatActivityDate(timestamp: string, timeZone: string): string {
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestamp)
  const utcTimestamp = hasTimezone ? timestamp : `${timestamp}Z`

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'short',
    timeZone,
  }).format(new Date(utcTimestamp))
}
