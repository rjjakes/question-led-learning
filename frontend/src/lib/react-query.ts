import type { DefaultOptions, UseMutationOptions } from "@tanstack/react-query"

// Bulletproof React's defaults (src/lib/react-query.ts). With no refetch on window focus, a question the learner
// is answering isn't restated again
export const queryConfig = {
  queries: {
    refetchOnWindowFocus: false,
    retry: false,
    staleTime: 1000 * 60,
  },
} satisfies DefaultOptions

export type ApiFnReturnType<
  FnType extends (...args: never[]) => Promise<unknown>,
> = Awaited<ReturnType<FnType>>

export type QueryConfig<T extends (...args: never[]) => unknown> = Omit<
  ReturnType<T>,
  "queryKey" | "queryFn"
>

export type MutationConfig<
  MutationFnType extends (...args: never[]) => Promise<unknown>,
> = UseMutationOptions<
  ApiFnReturnType<MutationFnType>,
  Error,
  Parameters<MutationFnType>[0]
>
