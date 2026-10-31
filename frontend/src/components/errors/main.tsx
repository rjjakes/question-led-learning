import { Button } from "@/components/ui/button"

/** The app's error screen, shown by the error boundary around the whole app. */
export const MainErrorFallback = () => {
  return (
    <div
      role="alert"
      className="flex h-svh w-full flex-col items-center justify-center gap-4"
    >
      <h2 className="text-lg font-semibold">Something went wrong.</h2>
      <Button onClick={() => window.location.assign(window.location.origin)}>
        Refresh
      </Button>
    </div>
  )
}
