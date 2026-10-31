import { ErrorBoundary } from "react-error-boundary"

import { ContentLayout } from "@/components/layouts/content-layout"
import { CoursesList } from "@/features/courses/components/courses-list"

const CoursesRoute = () => {
  return (
    <ContentLayout title="Courses">
      <ErrorBoundary
        fallback={<p>The courses couldn't be shown. Refresh the page.</p>}
      >
        <CoursesList />
      </ErrorBoundary>
    </ContentLayout>
  )
}

export default CoursesRoute
