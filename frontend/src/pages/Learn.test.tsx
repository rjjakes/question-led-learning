import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, test } from "vitest"

import { mockApi, place, renderAt } from "@/test/app"
import type { Outcome } from "@/types/api"

const QUESTION = { id: 7, restatement: 0, text: "Scenario.\n\nQuestion?" }

test("a failed answer is restated, then the answer is shown, then the course ends", async () => {
  const user = userEvent.setup()
  let current = place(QUESTION)
  const outcomes: Outcome[] = [
    {
      passed: false,
      feedback: "A point is missing.",
      step: "restate",
      restated: "More help.",
      model_answer: null,
    },
    {
      passed: false,
      feedback: "Still missing.",
      step: "reveal",
      restated: null,
      model_answer: "The answer.",
    },
  ]
  const sent: unknown[] = []
  mockApi((method, url, body) => {
    if (url !== "/api/learn/5/2") return [404, { detail: "Not Found" }]
    if (method === "GET") return [200, current]
    sent.push(body)
    return [200, outcomes.shift()]
  })
  renderAt("/learn/5/2")

  await user.type(await screen.findByLabelText("Your answer"), "Ignore it")
  await user.click(screen.getByRole("button", { name: "Submit answer" }))
  expect(await screen.findByText("A point is missing.")).toBeInTheDocument()
  expect(screen.getByText("More help.")).toBeInTheDocument()
  const retry = screen.getByLabelText("Try again (restatement 1 of 2)")
  expect(retry).toHaveValue("")

  await user.type(retry, "Report it")
  await user.click(screen.getByRole("button", { name: "Submit answer" }))
  expect(await screen.findByText("The answer.")).toBeInTheDocument()
  expect(screen.queryByRole("textbox")).not.toBeInTheDocument()
  expect(sent).toEqual([
    {
      question_id: 7,
      restatement: 0,
      shown_text: QUESTION.text,
      answer: "Ignore it",
    },
    {
      question_id: 7,
      restatement: 1,
      shown_text: "More help.",
      answer: "Report it",
    },
  ])

  current = place(null)
  await user.click(screen.getByRole("button", { name: "Next question" }))
  expect(
    await screen.findByText("You have answered every question.")
  ).toBeInTheDocument()
})

test("an answer that couldn't be scored can be sent again", async () => {
  const user = userEvent.setup()
  mockApi((method) =>
    method === "GET"
      ? [200, place(QUESTION)]
      : [503, { detail: "The answer couldn't be scored; send it again" }]
  )
  renderAt("/learn/5/2")

  await user.type(await screen.findByLabelText("Your answer"), "My answer")
  await user.click(screen.getByRole("button", { name: "Submit answer" }))
  expect(
    await screen.findByText(
      "Your answer couldn't be scored just now. Please send it again."
    )
  ).toBeInTheDocument()
  expect(screen.getByLabelText("Your answer")).toHaveValue("My answer")
})
