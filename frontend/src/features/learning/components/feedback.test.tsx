import { render, screen } from "@testing-library/react"
import { expect, test } from "vitest"

import type { Outcome } from "@/types/api"

import { Feedback } from "./feedback"

const outcome = (passed: boolean): Outcome => ({
  passed,
  feedback: "Feedback.",
  step: passed ? "next" : "restate",
  restated: passed ? null : "Restated.",
  model_answer: null,
})

test("a passed answer's feedback starts with the check icon", () => {
  render(<Feedback outcome={outcome(true)} />)
  expect(screen.getByRole("alert").firstElementChild).toHaveClass(
    "lucide-circle-check"
  )
})

test("a failed answer's feedback starts with the triangle icon", () => {
  render(<Feedback outcome={outcome(false)} />)
  expect(screen.getByRole("alert").firstElementChild).toHaveClass(
    "lucide-triangle-alert"
  )
})
