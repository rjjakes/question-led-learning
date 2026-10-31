import { useNavigate } from "react-router"

import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { paths } from "@/config/paths"

import { useStartCourse } from "../api/start-course"

type StartCourseProps = {
  courseId: number
}

/** Starts the course and opens its first question. */
export const StartCourse = ({ courseId }: StartCourseProps) => {
  const navigate = useNavigate()
  const startCourseMutation = useStartCourse({
    mutationConfig: {
      onSuccess: ({ learner_id }) =>
        navigate(paths.learn.getHref(learner_id, courseId)),
    },
  })

  return (
    <Button
      disabled={startCourseMutation.isPending}
      onClick={() => startCourseMutation.mutate({ courseId })}
    >
      {startCourseMutation.isPending && <Spinner />}
      Start
    </Button>
  )
}
