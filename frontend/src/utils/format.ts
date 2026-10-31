export const plural = (n: number, word: string) =>
  n === 1 ? `${n} ${word}` : `${n} ${word}s`
