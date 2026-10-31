import { toast } from "@/components/ui/toast"

/** A reply that isn't 2xx. status is its HTTP status. */
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    const reply = await res.json().catch(() => ({}))
    const message =
      typeof reply.detail === "string" ? reply.detail : res.statusText
    // Every failed request is shown here, once (Bulletproof React, docs/error-handling.md)
    toast.add({ type: "error", title: "Error", description: message })
    throw new ApiError(res.status, message)
  }
  return res.json()
}

/** The one client for the backend's JSON routes (lms/server/api.py) */
export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
}
