import type { BookDetail } from "../book-types"

type WordFile = { download_url: string; filename: string }

export async function downloadWord(
  book: Pick<BookDetail, "revision" | "automatic_result"> | null,
  language: "pt-BR" | "es",
  exportWord: () => Promise<WordFile | undefined>,
  startDownload: (file: WordFile) => void,
) {
  // The download endpoint still rejects an artifact if the saved revision changed.
  const ready = book?.automatic_result?.revision === book?.revision
    ? book?.automatic_result?.files[language] : undefined
  const file = ready ?? await exportWord()
  if (file) startDownload(file)
}
