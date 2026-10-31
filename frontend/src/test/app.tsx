import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { vi } from "vitest"

import { AppRoutes } from "@/App"
import type { Place, QuestionShown } from "@/types/api"

/** The app at path, with a fresh query cache. */
export function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

/** Answers the app's API calls with reply(method, url, body), which gives the status and the JSON. */
export function mockApi(
  reply: (method: string, url: string, body: unknown) => [number, unknown]
) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) : undefined
      const [status, json] = reply(init?.method ?? "GET", url, body)
      return new Response(JSON.stringify(json), {
        status,
        headers: { "Content-Type": "application/json" },
      })
    })
  )
}

export function place(question: QuestionShown | null): Place {
  return {
    course_id: 2,
    course_title: "Staying secure at work",
    number: question ? 1 : null,
    total: 1,
    max_restatements: 2,
    question,
  }
}
