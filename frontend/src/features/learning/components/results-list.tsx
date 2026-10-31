import { Badge } from "@/components/ui/badge"
import { Card, CardAction, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"
import type { Result } from "@/types/api"
import { plural } from "@/utils/format"

import { useResults } from "../api/get-results"

type ResultsListProps = {
  learnerId: string
  courseId: string
}

const resultText = (result: Result) => {
  if (!result.passed) return "Answer shown"
  return result.restatements === 0
    ? "Passed first time"
    : `Passed after ${plural(result.restatements, "restatement")}`
}

/**
 * Each question the learner has finished, with whether they passed it and
 * after how many restatements, or were shown the answer.
 */
export const ResultsList = ({ learnerId, courseId }: ResultsListProps) => {
  const resultsQuery = useResults({ learnerId, courseId })

  if (resultsQuery.isLoading) return <Spinner />

  const results = resultsQuery.data
  if (!results) return null

  return (
    <ol className="flex flex-col gap-3">
      {results.map((result) => (
        <li key={result.number}>
          <Card size="sm">
            <CardHeader>
              <CardTitle>
                {result.number}. {result.question}
              </CardTitle>
              <CardAction>
                <Badge variant={result.passed ? "secondary" : "outline"}>
                  {resultText(result)}
                </Badge>
              </CardAction>
            </CardHeader>
          </Card>
        </li>
      ))}
    </ol>
  )
}
