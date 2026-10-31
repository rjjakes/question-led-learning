import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Suspense, useState, type ReactNode } from "react"
import { ErrorBoundary } from "react-error-boundary"

import { MainErrorFallback } from "@/components/errors/main"
import { ThemeProvider } from "@/components/theme-provider"
import { Spinner } from "@/components/ui/spinner"
import { Toaster } from "@/components/ui/toast"
import { queryConfig } from "@/lib/react-query"

type AppProviderProps = {
  children: ReactNode
}

export const AppProvider = ({ children }: AppProviderProps) => {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: queryConfig })
  )

  return (
    <Suspense
      fallback={
        <div className="flex h-svh w-full items-center justify-center">
          <Spinner />
        </div>
      }
    >
      <ErrorBoundary FallbackComponent={MainErrorFallback}>
        <ThemeProvider>
          <QueryClientProvider client={queryClient}>
            {children}
            <Toaster />
          </QueryClientProvider>
        </ThemeProvider>
      </ErrorBoundary>
    </Suspense>
  )
}
