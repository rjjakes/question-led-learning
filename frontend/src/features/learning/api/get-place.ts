import { queryOptions, useQuery } from "@tanstack/react-query"

import { api } from "@/lib/api-client"
import type { QueryConfig } from "@/lib/react-query"
import type { Place } from "@/types/api"

/** The learner's current question, or none at the end of the course. */
export const getPlace = ({
  learnerId,
  courseId,
}: {
  learnerId: string
  courseId: string
}): Promise<Place> => {
  return api.get(`/learn/${learnerId}/${courseId}`)
}

export const getPlaceQueryOptions = (learnerId: string, courseId: string) => {
  return queryOptions({
    queryKey: ["place", learnerId, courseId],
    queryFn: () => getPlace({ learnerId, courseId }),
  })
}

type UsePlaceOptions = {
  learnerId: string
  courseId: string
  queryConfig?: QueryConfig<typeof getPlaceQueryOptions>
}

export const usePlace = ({
  learnerId,
  courseId,
  queryConfig,
}: UsePlaceOptions) => {
  return useQuery({
    ...getPlaceQueryOptions(learnerId, courseId),
    ...queryConfig,
  })
}
