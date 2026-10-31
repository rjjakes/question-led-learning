export function plural(n: number, word: string) {
  return n === 1 ? `${n} ${word}` : `${n} ${word}s`
}
