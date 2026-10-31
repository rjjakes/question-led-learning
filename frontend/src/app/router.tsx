import { useMemo, type ComponentType } from "react"
import { createBrowserRouter } from "react-router"
import { RouterProvider } from "react-router/dom"

import { paths } from "@/config/paths"

// Each route file loads when it's first needed (Bulletproof React, src/app/router.tsx)
const convert = (m: { default: ComponentType }) => ({ Component: m.default })

export const createAppRouter = () =>
  createBrowserRouter([
    {
      path: paths.courses.path,
      lazy: () => import("./routes/courses").then(convert),
    },
    {
      path: paths.learn.path,
      lazy: () => import("./routes/learn").then(convert),
    },
    {
      path: "*",
      lazy: () => import("./routes/not-found").then(convert),
    },
  ])

export const AppRouter = () => {
  const router = useMemo(() => createAppRouter(), [])

  return <RouterProvider router={router} />
}
