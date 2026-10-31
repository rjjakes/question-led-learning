export const paths = {
  courses: {
    path: "/",
    getHref: () => "/",
  },
  learn: {
    path: "/learn/:learnerId/:courseId",
    getHref: (learnerId: number | string, courseId: number | string) =>
      `/learn/${learnerId}/${courseId}`,
  },
} as const
