import { useCallback, useEffect, useRef, useState } from "react"
import type { BookDetail, BookSummary } from "./book-types"
import { downloadWord } from "./lib/download"

export async function api<T>(path: string, data?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { method: data === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json" }, body: data === undefined ? undefined : JSON.stringify(data), signal })
  if (!response.headers.get("content-type")?.includes("application/json")) throw new Error("O servidor não respondeu. Confira o terminal e tente atualizar.")
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.error || "Não foi possível concluir. Tente novamente.")
  return payload as T
}

export function useBooks() {
  const [projects, setProjects] = useState<BookSummary[]>([])
  const [projectId, setProjectId] = useState<string | null>(null)
  const [chunkId, setChunkId] = useState<string | null>(null)
  const [detail, setDetail] = useState<BookDetail | null>(null)
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>("loading")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const mounted = useRef(true)
  const waiting = useRef(new Map<string, (() => void)[]>())

  const refreshList = useCallback(async (signal?: AbortSignal) => {
    const result = await api<{ projects: BookSummary[]; active_project_id: string | null }>("/api/books", undefined, signal)
    if (mounted.current) { setProjects(result.projects); setActiveProjectId(result.active_project_id) }
    return result.projects
  }, [])

  useEffect(() => {
    mounted.current = true
    const controller = new AbortController()
    refreshList(controller.signal).then(list => {
      if (!controller.signal.aborted) { let saved: string | null = null; try { saved = localStorage.getItem("revisor-project") } catch { /* Storage may be unavailable. */ } setProjectId(list.find(p => p.id === saved)?.id ?? list[0]?.id ?? null); setBusy(null) }
    }).catch(err => { if (!controller.signal.aborted) { setError(err.message); setBusy(null) } })
    return () => { controller.abort(); mounted.current = false }
  }, [refreshList])

  const loadDetail = useCallback(async (signal?: AbortSignal) => {
    if (!projectId) return
    const suffix = chunkId ? `?chunk=${encodeURIComponent(chunkId)}` : ""
    const result = await api<BookDetail>(`/api/books/${projectId}${suffix}`, undefined, signal)
    if (mounted.current && !signal?.aborted) {
      setDetail(result)
      const id = result.current?.id
      if (id) { waiting.current.get(id)?.forEach(resolve => resolve()); waiting.current.delete(id) }
    }
    return result
  }, [projectId, chunkId])

  useEffect(() => {
    if (!projectId) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    async function poll() {
      try {
        const [result] = await Promise.all([loadDetail(controller.signal), refreshList(controller.signal)])
        if (!controller.signal.aborted && result && (["running", "stopping"].includes(result.job?.status ?? "") || Boolean(activeProjectId))) timer = setTimeout(poll, 1200)

      } catch (err) {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Não foi possível carregar o livro.")
        waiting.current.forEach(list => list.forEach(resolve => resolve())); waiting.current.clear()
      }
    }
    void poll()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [projectId, loadDetail, refreshList, detail?.job?.id, activeProjectId])

  /** Open a chunk; resolves when its text is on screen, so the button that asked can show progress. */
  function showChunk(id: string) {
    if (detail?.current?.id === id) { setChunkId(id); return Promise.resolve() }  // Pin it: after an action the server may show another one.
    return new Promise<void>(resolve => {
      waiting.current.set(id, [...(waiting.current.get(id) ?? []), resolve])
      setChunkId(id)
    })
  }
  function selectProject(id: string) { try { localStorage.setItem("revisor-project", id) } catch { /* Keep the session usable without storage. */ } setProjectId(id); setDetail(null); setChunkId(null); setError(""); setNotice("") }
  async function retryLoading() {
    setBusy("loading"); setError("")
    try {
      const list = await refreshList()
      let remembered: string | null = null
      try { remembered = localStorage.getItem("revisor-project") } catch { /* Storage is optional. */ }
      const chosen = list.find(p => p.id === projectId)?.id ?? list.find(p => p.id === remembered)?.id ?? list[0]?.id ?? null
      if (chosen !== projectId) { setProjectId(chosen); setDetail(null); setChunkId(null) }
      else if (chosen) await loadDetail()
    } catch (err) { setError(err instanceof Error ? err.message : "Não foi possível atualizar seus livros.") }
    finally { if (mounted.current) setBusy(null) }
  }
  async function action(operation: string, data: unknown = {}) {
    if (!projectId) return
    setBusy(operation); setError(""); setNotice("")
    try {
      const result = await api<Record<string, unknown>>(`/api/books/${projectId}/${operation}`, data)
      if (operation === "approve" || operation === "approve-all") setChunkId(null)
      await loadDetail(); await refreshList()
      return result
    } catch (err) {
      setError(err instanceof Error ? err.message : "A operação falhou.")
      await loadDetail().catch(() => {})
    } finally { if (mounted.current) setBusy(null) }
  }

  async function removeBook(id: string) {
    setBusy("remove"); setError(""); setNotice("")
    try {
      await api(`/api/books/${id}/remove`, {})
      const list = await refreshList()
      const next = list[0]?.id ?? null
      try { if (next) localStorage.setItem("revisor-project", next); else localStorage.removeItem("revisor-project") } catch { /* Storage is optional. */ }
      setDetail(null); setChunkId(null); setProjectId(next)
      return true
    } catch (err) { setError(err instanceof Error ? err.message : "Não foi possível remover o livro.") }
    finally { if (mounted.current) setBusy(null) }
    return false
  }

  async function importBook(name: string, source: File, destination?: File) {
    const encode = (file: File) => new Promise<{ name: string; data: string }>((resolve, reject) => {
      if (file.size > 32 * 1024 * 1024) { reject(new Error("Cada Word deve ter até 32 MB.")); return }
      if (!file.name.toLowerCase().endsWith(".docx")) { reject(new Error("Selecione um arquivo Word .docx.")); return }
      const reader = new FileReader()
      reader.onload = () => resolve({ name: file.name, data: String(reader.result).split(",")[1] })
      reader.onerror = () => reject(new Error("Não foi possível ler o arquivo. Selecione-o novamente."))
      reader.readAsDataURL(file)
    })
    setBusy("import"); setError(""); setNotice("")
    try {
      const files = await Promise.all([encode(source), destination ? encode(destination) : Promise.resolve(null)])
      const result = await api<{ id: string }>("/api/books/import", { name, source: files[0], destination: files[1] })
      await refreshList(); selectProject(result.id)
      setNotice("Livro importado. Confira o escopo antes de começar.")
      return true
    } catch (err) { setError(err instanceof Error ? err.message : "Não foi possível importar o Word.") }
    finally { if (mounted.current) setBusy(null) }
    return false
  }

  async function download(language: "pt-BR" | "es") {
    if (!projectId) return
    setBusy("export"); setError(""); setNotice("")
    try {
      await downloadWord(detail, language,
        () => api<{ download_url: string; filename: string }>(`/api/books/${projectId}/export`, { language }),
        result => {
          const anchor = document.createElement("a")
          anchor.href = result.download_url; anchor.download = result.filename; anchor.click()
          setNotice("O download foi iniciado.")
        })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível baixar o Word.")
    } finally { if (mounted.current) setBusy(null) }
  }
  return { projects, projectId, chunkId, setChunkId, showChunk, removeBook, selectProject, detail, busy, error, notice, activeProjectId, action, importBook, download, refreshList, loadDetail, retryLoading }
}
