import { queryOptions, useQuery } from "@tanstack/react-query"

import { api } from "@/lib/api-client"
import type { QueryConfig } from "@/lib/react-query"
import type { Result } from "@/types/api"

/**
 * How each question the learner has finished went, in course order.
 */
export const getResults = ({
  learnerId,
  courseId,
}: {
  learnerId: string
  courseId: string
}): Promise<Result[]> => {
  return api.get(`/learn/${learnerId}/${courseId}/results`)
}

export const getResultsQueryOptions = (learnerId: string, courseId: string) => {
  return queryOptions({
    queryKey: ["results", learnerId, courseId],
    queryFn: () => getResults({ learnerId, courseId }),
  })
}

type UseResultsOptions = {
  learnerId: string
  courseId: string
  queryConfig?: QueryConfig<typeof getResultsQueryOptions>
}

export const useResults = ({
  learnerId,
  courseId,
  queryConfig,
}: UseResultsOptions) => {
  return useQuery({
    ...getResultsQueryOptions(learnerId, courseId),
    ...queryConfig,
  })
}
