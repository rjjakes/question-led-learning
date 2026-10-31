import { Link } from "react-router"

import { buttonVariants } from "@/components/ui/button"
import { paths } from "@/config/paths"
import { cn } from "@/lib/utils"

import { ResultsList } from "./results-list"

type CourseCompleteProps = {
  learnerId: string
  courseId: string
}

/**
 * Summary of results.
 */
export const CourseComplete = ({
  learnerId,
  courseId,
}: CourseCompleteProps) => {
  return (
    <>
      <p>You have answered every question.</p>
      <ResultsList learnerId={learnerId} courseId={courseId} />
      <Link
        to={paths.courses.getHref()}
        className={cn(buttonVariants(), "self-start")}
      >
        Courses
      </Link>
    </>
  )
}
