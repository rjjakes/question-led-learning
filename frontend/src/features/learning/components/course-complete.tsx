import { Link } from "react-router"

import { buttonVariants } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { paths } from "@/config/paths"

export const CourseComplete = () => {
  return (
    <Empty className="border">
      <EmptyHeader>
        <EmptyTitle>You have answered every question.</EmptyTitle>
      </EmptyHeader>
      <EmptyContent>
        <Link to={paths.courses.getHref()} className={buttonVariants()}>
          Courses
        </Link>
      </EmptyContent>
    </Empty>
  )
}
