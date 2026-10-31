import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type ModelAnswerProps = {
  answer: string
}

/** The question's answer, shown when the learner has run out of restatements. */
export const ModelAnswer = ({ answer }: ModelAnswerProps) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>The answer</CardTitle>
      </CardHeader>
      <CardContent className="whitespace-pre-wrap">{answer}</CardContent>
    </Card>
  )
}
