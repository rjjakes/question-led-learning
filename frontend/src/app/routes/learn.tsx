import { ErrorBoundary } from "react-error-boundary"
import { useParams } from "react-router"

import { ContentLayout } from "@/components/layouts/content-layout"
import { Spinner } from "@/components/ui/spinner"
import { usePlace } from "@/features/learning/api/get-place"
import { CourseComplete } from "@/features/learning/components/course-complete"
import { Question } from "@/features/learning/components/question"
import { plural } from "@/utils/format"

const LearnRoute = () => {
  const params = useParams()
  const learnerId = params.learnerId as string
  const courseId = params.courseId as string
  const placeQuery = usePlace({ learnerId, courseId })

  if (placeQuery.isLoading)
    return (
      <div className="flex h-48 w-full items-center justify-center">
        <Spinner />
      </div>
    )

  const place = placeQuery.data
  if (!place) return null

  const { question } = place
  return (
    <ContentLayout
      title={question ? place.course_title : "Course complete"}
      description={
        question
          ? `Question ${place.number} of ${place.total}`
          : plural(place.total, "question")
      }
    >
      <ErrorBoundary
        fallback={<p>The question couldn't be shown. Refresh the page.</p>}
      >
        {question ? (
          <Question
            key={question.id}
            learnerId={learnerId}
            courseId={courseId}
            question={question}
            maxRestatements={place.max_restatements}
          />
        ) : (
          <CourseComplete />
        )}
      </ErrorBoundary>
    </ContentLayout>
  )
}

export default LearnRoute
