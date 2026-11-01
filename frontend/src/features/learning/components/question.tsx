import { useIsFetching, useQueryClient } from "@tanstack/react-query"

import { ThinkingTime } from "@/components/thinking-time"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import type { QuestionShown } from "@/types/api"

import { getPlaceQueryOptions } from "../api/get-place"
import { useSendAnswer } from "../api/send-answer"
import { AnswerForm } from "./answer-form"
import { Feedback } from "./feedback"
import { ModelAnswer } from "./model-answer"

type QuestionProps = {
  learnerId: string
  courseId: string
  question: QuestionShown
  maxRestatements: number
}

/** One question: the learner answers it, then answers each restatement after a fail, until they pass or are
 * shown the answer. */
export const Question = ({
  learnerId,
  courseId,
  question,
  maxRestatements,
}: QuestionProps) => {
  const queryClient = useQueryClient()
  const placeKey = getPlaceQueryOptions(learnerId, courseId).queryKey
  const moving = useIsFetching({ queryKey: placeKey }) > 0
  const sendAnswerMutation = useSendAnswer()
  const outcome = sendAnswerMutation.data

  return (
    <>
      {outcome && <Feedback outcome={outcome} />}
      {!outcome || outcome.step === "restate" ? (
        <AnswerForm
          key={question.restatement}
          question={question}
          maxRestatements={maxRestatements}
          isPending={sendAnswerMutation.isPending}
          onSubmit={(data) =>
            sendAnswerMutation.mutate({ learnerId, courseId, question, data })
          }
        />
      ) : (
        <>
          {outcome.step === "reveal" && outcome.model_answer && (
            <ModelAnswer answer={outcome.model_answer} />
          )}
          <div className="flex flex-col items-start gap-2">
            <Button
              disabled={moving}
              onClick={() =>
                queryClient.invalidateQueries({ queryKey: placeKey })
              }
            >
              {moving && <Spinner />}
              Next question
            </Button>
            {moving && <ThinkingTime />}
          </div>
        </>
      )}
    </>
  )
}
