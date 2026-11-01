import { useEffect, useState } from "react"

/**
 * The seconds since it appeared, counting up from 1, shown below a button
 * while its request runs.
 */
export const ThinkingTime = () => {
  const [seconds, setSeconds] = useState(1)

  useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <p className="text-sm text-muted-foreground">{seconds}s • Thinking...</p>
  )
}
