import { useIsFetching, useQueryClient } from "@tanstack/react-query"
import { useState, type FormEvent } from "react"
import { Link, useParams } from "react-router-dom"

import {
  ApiError,
  placeKey,
  usePlace,
  useSendAnswer,
} from "@/api/useLearnerApi"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Empty,
  EmptyContent,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Field, FieldLabel } from "@/components/ui/field"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { plural } from "@/lib/plural"
import type { Outcome, Place, QuestionShown } from "@/types/api"

/** The learner's screen: the current question, the result of each answer, and the end of the course. */
export default function Learn() {
  const { learnerId = "", courseId = "" } = useParams()
  const place = usePlace(learnerId, courseId)

  if (place.isPending) return <Spinner />
  if (place.isError)
    return (
      <Alert variant="destructive">
        <AlertDescription>{place.error.message}</AlertDescription>
      </Alert>
    )

  const { question } = place.data
  return (
    <>
      <header>
        <h1 className="font-heading text-2xl font-semibold">
          {question ? place.data.course_title : "Course complete"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {question
            ? `Question ${place.data.number} of ${place.data.total}`
            : plural(place.data.total, "question")}
        </p>
      </header>
      {question ? (
        <Step
          key={`${question.id}-${question.restatement}`}
          learnerId={learnerId}
          courseId={courseId}
          place={place.data}
          question={question}
        />
      ) : (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>You have answered every question.</EmptyTitle>
          </EmptyHeader>
          <EmptyContent>
            <Link to="/" className={buttonVariants()}>
              Courses
            </Link>
          </EmptyContent>
        </Empty>
      )}
    </>
  )
}

/** One question: answered, then restated after a fail until the answer is shown or the learner moves on. */
function Step({
  learnerId,
  courseId,
  place,
  question,
}: {
  learnerId: string
  courseId: string
  place: Place
  question: QuestionShown
}) {
  const queryClient = useQueryClient()
  const send = useSendAnswer(learnerId, courseId)
  const [shown, setShown] = useState(question)
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const moving = useIsFetching({ queryKey: placeKey(learnerId, courseId) }) > 0

  function moveOn() {
    queryClient.invalidateQueries({ queryKey: placeKey(learnerId, courseId) })
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const answer = String(new FormData(event.currentTarget).get("answer"))
    send.mutate(
      {
        question_id: shown.id,
        restatement: shown.restatement,
        shown_text: shown.text,
        answer,
      },
      {
        onSuccess: (result) => {
          setOutcome(result)
          if (result.step === "restate")
            setShown({
              ...shown,
              restatement: shown.restatement + 1,
              text: result.restated ?? shown.text,
            })
        },
        onError: (error) => {
          // The answer isn't to the learner's place any more (sent twice, or from an old tab)
          if (error instanceof ApiError && error.status === 409) moveOn()
        },
      }
    )
  }

  const label =
    shown.restatement === 0
      ? "Your answer"
      : `Try again (restatement ${shown.restatement} of ${place.max_restatements})`

  return (
    <>
      {outcome && (
        <Alert>
          <AlertTitle>
            {outcome.passed ? "Good answer." : "Not quite."}
          </AlertTitle>
          <AlertDescription>{outcome.feedback}</AlertDescription>
        </Alert>
      )}
      {send.isError &&
        !(send.error instanceof ApiError && send.error.status === 409) && (
          <Alert variant="destructive">
            <AlertDescription>
              {send.error instanceof ApiError && send.error.status === 503
                ? "Your answer couldn't be scored just now. Please send it again."
                : send.error.message}
            </AlertDescription>
          </Alert>
        )}
      {(!outcome || outcome.step === "restate") && (
        <form
          key={shown.restatement}
          onSubmit={submit}
          className="flex flex-col gap-4"
        >
          <Card>
            <CardContent className="whitespace-pre-wrap">
              {shown.text}
            </CardContent>
          </Card>
          <Field>
            <FieldLabel htmlFor="answer">{label}</FieldLabel>
            <Textarea id="answer" name="answer" required className="min-h-36" />
          </Field>
          <Button
            type="submit"
            disabled={send.isPending}
            className="self-start"
          >
            {send.isPending && <Spinner />}
            Submit answer
          </Button>
        </form>
      )}
      {outcome?.step === "reveal" && (
        <Card>
          <CardHeader>
            <CardTitle>The answer</CardTitle>
          </CardHeader>
          <CardContent className="whitespace-pre-wrap">
            {outcome.model_answer}
          </CardContent>
        </Card>
      )}
      {outcome && outcome.step !== "restate" && (
        <Button onClick={moveOn} disabled={moving} className="self-start">
          {moving && <Spinner />}
          Next question
        </Button>
      )}
    </>
  )
}
