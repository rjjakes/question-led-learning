import { useMutation, useQuery } from "@tanstack/react-query"

import type { AnswerRequest, Course, Outcome, Place } from "@/types/api"

/** A reply that isn't 2xx. status is the HTTP status: 409 and 503 have meanings of their own (lms/server/api.py). */
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(
      res.status,
      typeof body.detail === "string" ? body.detail : res.statusText
    )
  }
  return res.json()
}

function post<T>(url: string, body?: unknown) {
  return request<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export function useCourses() {
  return useQuery({
    queryKey: ["courses"],
    queryFn: () => request<Course[]>("/api/courses"),
  })
}

export function useStartCourse() {
  return useMutation({
    mutationFn: (courseId: number) =>
      post<{ learner_id: number }>(`/api/courses/${courseId}/start`),
  })
}

export function placeKey(learnerId: string, courseId: string) {
  return ["place", learnerId, courseId]
}

/** The learner's current question, or none at the end of the course. */
export function usePlace(learnerId: string, courseId: string) {
  return useQuery({
    queryKey: placeKey(learnerId, courseId),
    queryFn: () => request<Place>(`/api/learn/${learnerId}/${courseId}`),
  })
}

export function useSendAnswer(learnerId: string, courseId: string) {
  return useMutation({
    mutationFn: (body: AnswerRequest) =>
      post<Outcome>(`/api/learn/${learnerId}/${courseId}`, body),
  })
}
