import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"

import { ThinkingTime } from "@/components/thinking-time"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Field, FieldError, FieldLabel } from "@/components/ui/field"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import type { QuestionShown } from "@/types/api"

import { sendAnswerInputSchema, type SendAnswerInput } from "../api/send-answer"

type AnswerFormProps = {
  question: QuestionShown
  maxRestatements: number
  defaultAnswer: string
  isPending: boolean
  onSubmit: (data: SendAnswerInput) => void
}

/** Shows the question as the learner should see it and collects their answer. */
export const AnswerForm = ({
  question,
  maxRestatements,
  defaultAnswer,
  isPending,
  onSubmit,
}: AnswerFormProps) => {
  const form = useForm<SendAnswerInput>({
    resolver: zodResolver(sendAnswerInputSchema),
    defaultValues: { answer: defaultAnswer },
  })

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="flex flex-col gap-4"
    >
      <Card>
        <CardContent className="whitespace-pre-wrap">
          {question.text}
        </CardContent>
      </Card>
      <Controller
        name="answer"
        control={form.control}
        render={({ field, fieldState }) => (
          <Field data-invalid={fieldState.invalid}>
            <FieldLabel htmlFor="answer">
              {question.restatement === 0
                ? "Your answer"
                : `Try again (restatement ${question.restatement} of ${maxRestatements})`}
            </FieldLabel>
            <Textarea
              {...field}
              id="answer"
              aria-invalid={fieldState.invalid}
              className="min-h-36"
            />
            {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
          </Field>
        )}
      />
      <div className="flex flex-col items-start gap-2">
        <Button type="submit" disabled={isPending}>
          {isPending && <Spinner />}
          Submit answer
        </Button>
        {isPending && <ThinkingTime />}
      </div>
    </form>
  )
}
