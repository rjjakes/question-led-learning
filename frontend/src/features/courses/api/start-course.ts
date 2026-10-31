import { useMutation } from "@tanstack/react-query"

import { api } from "@/lib/api-client"
import type { MutationConfig } from "@/lib/react-query"

/** Starts a course as a new learner. */
export const startCourse = ({
  courseId,
}: {
  courseId: number
}): Promise<{ learner_id: number }> => {
  return api.post(`/courses/${courseId}/start`)
}

type UseStartCourseOptions = {
  mutationConfig?: MutationConfig<typeof startCourse>
}

export const useStartCourse = ({
  mutationConfig,
}: UseStartCourseOptions = {}) => {
  return useMutation({
    ...mutationConfig,
    mutationFn: startCourse,
  })
}
