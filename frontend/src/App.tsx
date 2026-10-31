import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BrowserRouter, Route, Routes } from "react-router-dom"

import Courses from "@/pages/Courses"
import Learn from "@/pages/Learn"

// No refetch on window focus, as in NVIDIA's RAG Blueprint frontend (src/App.tsx). Here a refetch would also
// make a new restatement of the question the learner is answering
const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
})

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Courses />} />
      <Route path="/learn/:learnerId/:courseId" element={<Learn />} />
    </Routes>
  )
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-10">
          <AppRoutes />
        </main>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
