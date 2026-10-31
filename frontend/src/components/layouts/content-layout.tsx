import type { ReactNode } from "react"

type ContentLayoutProps = {
  title: string
  description?: string
  children: ReactNode
}

/** Every page: its title, a line under it, and its content. */
export const ContentLayout = ({
  title,
  description,
  children,
}: ContentLayoutProps) => {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-10">
      <header>
        <h1 className="font-heading text-2xl font-semibold">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </header>
      {children}
    </main>
  )
}
