import { queryOptions, useQuery } from "@tanstack/react-query"

import { api } from "@/lib/api-client"
import type { QueryConfig } from "@/lib/react-query"
import type { Course } from "@/types/api"

/** The courses with checked questions. */
export const getCourses = (): Promise<Course[]> => {
  return api.get("/courses")
}

export const getCoursesQueryOptions = () => {
  return queryOptions({
    queryKey: ["courses"],
    queryFn: getCourses,
  })
}

type UseCoursesOptions = {
  queryConfig?: QueryConfig<typeof getCoursesQueryOptions>
}

export const useCourses = ({ queryConfig }: UseCoursesOptions = {}) => {
  return useQuery({
    ...getCoursesQueryOptions(),
    ...queryConfig,
  })
}
