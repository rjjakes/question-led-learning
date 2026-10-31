import { useNavigate } from "react-router-dom"

import { useCourses, useStartCourse } from "@/api/useLearnerApi"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Empty, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Spinner } from "@/components/ui/spinner"
import { plural } from "@/lib/plural"

export default function Courses() {
  const courses = useCourses()
  const start = useStartCourse()
  const navigate = useNavigate()

  function begin(courseId: number) {
    start.mutate(courseId, {
      onSuccess: ({ learner_id }) =>
        navigate(`/learn/${learner_id}/${courseId}`),
    })
  }

  return (
    <>
      <h1 className="font-heading text-2xl font-semibold">Courses</h1>
      {courses.isPending && <Spinner />}
      {courses.isError && (
        <Alert variant="destructive">
          <AlertDescription>The courses couldn't be loaded.</AlertDescription>
        </Alert>
      )}
      {start.isError && (
        <Alert variant="destructive">
          <AlertDescription>The course couldn't be started.</AlertDescription>
        </Alert>
      )}
      {courses.data?.length === 0 && (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>No courses with questions yet.</EmptyTitle>
          </EmptyHeader>
        </Empty>
      )}
      {!!courses.data?.length && (
        <ul className="flex flex-col gap-3">
          {courses.data.map((course) => (
            <li key={course.id}>
              <Card size="sm">
                <CardHeader>
                  <CardTitle>{course.title}</CardTitle>
                  <CardDescription>
                    {plural(course.questions, "question")}
                  </CardDescription>
                  <CardAction>
                    <Button
                      disabled={start.isPending}
                      onClick={() => begin(course.id)}
                    >
                      {start.isPending && start.variables === course.id && (
                        <Spinner />
                      )}
                      Start
                    </Button>
                  </CardAction>
                </CardHeader>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
