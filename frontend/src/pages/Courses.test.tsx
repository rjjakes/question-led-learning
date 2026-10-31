import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, test } from "vitest"

import { mockApi, place, renderAt } from "@/test/app"

test("starting a course opens its first question", async () => {
  const user = userEvent.setup()
  mockApi((method, url) => {
    if (url === "/api/courses")
      return [200, [{ id: 2, title: "Staying secure at work", questions: 10 }]]
    if (method === "POST" && url === "/api/courses/2/start")
      return [200, { learner_id: 5 }]
    if (url === "/api/learn/5/2")
      return [
        200,
        place({ id: 7, restatement: 0, text: "Scenario.\n\nQuestion?" }),
      ]
    return [404, { detail: "Not Found" }]
  })
  renderAt("/")

  expect(await screen.findByText("10 questions")).toBeInTheDocument()
  await user.click(screen.getByRole("button", { name: "Start" }))
  expect(await screen.findByText(/Question\?/)).toBeInTheDocument()
  expect(screen.getByText("Question 1 of 1")).toBeInTheDocument()
})
