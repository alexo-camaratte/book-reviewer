import assert from "node:assert/strict"
import { test } from "node:test"
import { downloadWord } from "./download.ts"

const files = {
  es: { path: "es.docx", filename: "Livro ES REVISADO.docx", download_url: "/downloads/books/livro/es" },
  "pt-BR": { path: "pt.docx", filename: "Livro PT REVISADO.docx", download_url: "/downloads/books/livro/pt-BR" },
}
const book = { revision: 3, automatic_result: { revision: 3, files } }

for (const language of ["es", "pt-BR"] as const) {
  test(`download ${language} pronto começa sem exportar nem aguardar outra requisição`, async () => {
    let exports = 0
    const started: unknown[] = []
    const download = downloadWord(book, language, async () => { exports++; return files[language] }, file => started.push(file))
    assert.equal(exports, 0)
    assert.deepEqual(started, [files[language]])
    await download
  })
}

test("sem entrega atual, espera somente a exportação e inicia o arquivo retornado", async () => {
  for (const snapshot of [null, { revision: 4, automatic_result: book.automatic_result }, { revision: 3, automatic_result: null }]) {
    const events: string[] = []
    await downloadWord(snapshot, "es", async () => { events.push("export"); return files.es }, file => {
      events.push("download")
      assert.deepEqual(file, files.es)
    })
    assert.deepEqual(events, ["export", "download"])
  }
})

test("erro de exportação não inicia download nem se perde", async () => {
  await assert.rejects(downloadWord(null, "es", async () => { throw new Error("Exportação falhou") }, () => assert.fail("download indevido")), /Exportação falhou/)
})
