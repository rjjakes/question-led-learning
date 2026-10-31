import {
  Card,
  CardAction,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Empty, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Spinner } from "@/components/ui/spinner"
import { plural } from "@/utils/format"

import { useCourses } from "../api/get-courses"
import { StartCourse } from "./start-course"

export const CoursesList = () => {
  const coursesQuery = useCourses()

  if (coursesQuery.isLoading) return <Spinner />

  const courses = coursesQuery.data
  if (!courses) return null

  if (courses.length === 0)
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyTitle>No courses with questions yet.</EmptyTitle>
        </EmptyHeader>
      </Empty>
    )

  return (
    <ul className="flex flex-col gap-3">
      {courses.map((course) => (
        <li key={course.id}>
          <Card size="sm">
            <CardHeader>
              <CardTitle>{course.title}</CardTitle>
              <CardDescription>
                {plural(course.questions, "question")}
              </CardDescription>
              <CardAction>
                <StartCourse courseId={course.id} />
              </CardAction>
            </CardHeader>
          </Card>
        </li>
      ))}
    </ul>
  )
}
