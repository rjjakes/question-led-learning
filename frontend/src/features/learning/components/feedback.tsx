import { AlertTriangleIcon, CheckCircle2Icon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import type { Outcome } from "@/types/api"

type FeedbackProps = {
  outcome: Outcome
}

/** 
 * The scorer's verdict on an answer, with an icon for pass or fail. 
 */
export const Feedback = ({ outcome }: FeedbackProps) => {
  return (
    <Alert>
      {outcome.passed ? (
        <CheckCircle2Icon className="size-12" />
      ) : (
        <AlertTriangleIcon className="size-12" />
      )}
      <AlertTitle>{outcome.passed ? "Good answer." : "Not quite."}</AlertTitle>
      <AlertDescription>{outcome.feedback}</AlertDescription>
    </Alert>
  )
}
