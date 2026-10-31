// What the learner API takes and returns (the Pydantic models in lms/server/api.py)

export type Course = {
  id: number
  title: string
  questions: number
}

export type QuestionShown = {
  id: number
  restatement: number
  text: string
}

export type Place = {
  course_id: number
  course_title: string
  number: number | null
  total: number
  max_restatements: number
  question: QuestionShown | null
}

export type AnswerRequest = {
  question_id: number
  restatement: number
  shown_text: string
  answer: string
}

export type Outcome = {
  passed: boolean
  feedback: string
  step: "next" | "restate" | "reveal"
  restated: string | null
  model_answer: string | null
}
