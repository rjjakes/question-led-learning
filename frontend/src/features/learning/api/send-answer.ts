import { useMutation, useQueryClient } from "@tanstack/react-query"
import { z } from "zod"

import { ApiError, api } from "@/lib/api-client"
import type { MutationConfig } from "@/lib/react-query"
import type { Outcome, QuestionShown } from "@/types/api"

import { getPlaceQueryOptions } from "./get-place"

export const sendAnswerInputSchema = z.object({
  answer: z.string().trim().min(1, "Write an answer first."),
})

export type SendAnswerInput = z.infer<typeof sendAnswerInputSchema>

/** Sends the learner's answer to the question as shown, and gets it scored. */
export const sendAnswer = ({
  learnerId,
  courseId,
  question,
  data,
}: {
  learnerId: string
  courseId: string
  question: QuestionShown
  data: SendAnswerInput
}): Promise<Outcome> => {
  return api.post(`/learn/${learnerId}/${courseId}`, {
    question_id: question.id,
    restatement: question.restatement,
    shown_text: question.text,
    answer: data.answer,
  })
}

type UseSendAnswerOptions = {
  mutationConfig?: MutationConfig<typeof sendAnswer>
}

export const useSendAnswer = ({
  mutationConfig,
}: UseSendAnswerOptions = {}) => {
  const queryClient = useQueryClient()

  const { onSuccess, onError, ...restConfig } = mutationConfig || {}

  return useMutation({
    onSuccess: (outcome, variables, ...args) => {
      // The learner answers the restated question next. It goes into the cached place, as the
      // backend makes a new restatement each time the place is fetched
      const { restated } = outcome
      if (outcome.step === "restate" && restated !== null)
        queryClient.setQueryData(
          getPlaceQueryOptions(variables.learnerId, variables.courseId)
            .queryKey,
          (place) =>
            place?.question
              ? {
                  ...place,
                  question: {
                    ...place.question,
                    restatement: place.question.restatement + 1,
                    text: restated,
                  },
                }
              : place
        )
      onSuccess?.(outcome, variables, ...args)
    },
    onError: (error, variables, ...args) => {
      // The answer isn't to the learner's place any more (sent twice, or from an old tab)
      if (error instanceof ApiError && error.status === 409)
        queryClient.invalidateQueries({
          queryKey: getPlaceQueryOptions(
            variables.learnerId,
            variables.courseId
          ).queryKey,
        })
      onError?.(error, variables, ...args)
    },
    ...restConfig,
    mutationFn: sendAnswer,
  })
}
