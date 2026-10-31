import { Link } from "react-router"

import { ContentLayout } from "@/components/layouts/content-layout"
import { buttonVariants } from "@/components/ui/button"
import { paths } from "@/config/paths"

const NotFoundRoute = () => {
  return (
    <ContentLayout
      title="Not found"
      description="There's no page at this address."
    >
      <Link
        to={paths.courses.getHref()}
        replace
        className={buttonVariants({ className: "self-start" })}
      >
        Courses
      </Link>
    </ContentLayout>
  )
}

export default NotFoundRoute
