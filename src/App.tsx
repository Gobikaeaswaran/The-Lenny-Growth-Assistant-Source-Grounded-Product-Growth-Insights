import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowUp, BookOpen, ChevronDown, FileText, LoaderCircle, Menu, Plus, Sparkles, SquarePen, X } from 'lucide-react'
import './workbench.css'
import './provider-status.css'

type Model = 'ollama' | 'anthropic'
type ChatMode = 'quote' | 'answer' | 'essay' | 'artifact'
type Citation = { title: string; speaker: string; timestamp?: string; url?: string }
type Message = { id?: string; role: 'user' | 'assistant'; content: string; citations?: Citation[] }
type Session = { id: string; title: string }
type Artifact = { type: string; title: string; content: string }
const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const starterQuestions = ['How do great teams find product-market fit?', 'What makes a compelling growth loop?', 'How should I run better customer interviews?']

function App() {
  const [model, setModel] = useState<Model>('ollama')
  const [mode, setMode] = useState<ChatMode>('quote')
  const [sessions, setSessions] = useState<Session[]>([])
  const [sessionId, setSessionId] = useState<string>()
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [artifact, setArtifact] = useState<Artifact>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [health, setHealth] = useState<'checking' | 'online' | 'offline'>('checking')
  const [providerStatuses, setProviderStatuses] = useState<Record<Model, string>>({ ollama: 'checking', anthropic: 'checking' })
  const [mobileHistory, setMobileHistory] = useState(false)

  useEffect(() => {
    async function refreshHealth() {
      try {
        const response = await fetch(`${API}/health`)
        const result = await response.json() as { providers?: Record<Model, string> }
        setHealth(response.ok ? 'online' : 'offline')
        if (result.providers) setProviderStatuses(result.providers)
      } catch {
        setHealth('offline')
        setProviderStatuses({ ollama: 'unavailable', anthropic: 'unavailable' })
      }
    }

    void refreshHealth()
    const healthInterval = window.setInterval(() => void refreshHealth(), 30000)
    void fetch(`${API}/api/sessions`).then((response) => response.ok ? response.json() : []).then(setSessions).catch(() => setSessions([]))
    return () => window.clearInterval(healthInterval)
  }, [])

  async function startSession() {
    const response = await fetch(`${API}/api/sessions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: 'New conversation' }) })
    if (!response.ok) throw new Error('Could not create a conversation')
    const session = await response.json() as Session
    setSessionId(session.id)
    setSessions((current) => [session, ...current])
    return session.id
  }

  async function selectSession(session: Session) {
    setSessionId(session.id)
    setMessages([])
    setArtifact(undefined)
    setMobileHistory(false)
    try {
      const response = await fetch(`${API}/api/sessions/${session.id}/messages`)
      if (response.ok) setMessages(await response.json())
    } catch { setError('Could not load this conversation.') }
  }

  async function submit(event?: FormEvent, prompt = draft) {
    event?.preventDefault()
    const question = prompt.trim()
    if (!question || loading) return
    setError('')
    setDraft('')
    setLoading(true)
    const userMessage: Message = { role: 'user', content: question }
    const assistantMessage: Message = { id: crypto.randomUUID(), role: 'assistant', content: '' }
    setMessages((current) => [...current, userMessage, assistantMessage])
    function updateAssistantMessage(content: string | undefined, citations: Citation[] | undefined) {
      setMessages((current) => {
        const exactIndex = current.findIndex((item) => item.id === assistantMessage.id)
        const assistantIndex = exactIndex >= 0 ? exactIndex : current.map((item) => item.role === 'assistant' && item.content === '').lastIndexOf(true)
        if (assistantIndex < 0) return current
        return current.map((item, index) => {
          if (index !== assistantIndex) return item
          return {
            ...item,
            id: assistantMessage.id,
            ...(content !== undefined ? { content } : {}),
            ...(citations !== undefined ? { citations } : {}),
          }
        })
      })
    }
    try {
      const activeId = sessionId ?? await startSession()
      const response = await fetch(`${API}/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: activeId, message: question, model, mode, stream: true }) })
      if (!response.ok || !response.body) throw new Error((await response.text()) || 'The assistant could not respond.')
      const emittedArtifact = await readChatStream(response, {
        onToken: (answer, citations) => updateAssistantMessage(answer, citations),
        onCitations: (citations) => updateAssistantMessage(undefined, citations),
      })
      if (emittedArtifact) setArtifact(emittedArtifact)
      setSessions((current) => current.map((session) => session.id === activeId && session.title === 'New conversation' ? { ...session, title: question.slice(0, 42) } : session))
    } catch (caught) {
      setMessages((current) => current.filter((item) => item !== userMessage && item !== assistantMessage))
      setError(caught instanceof Error ? caught.message : 'Something went wrong. Please try again.')
    } finally { setLoading(false) }
  }

  return <main className="app-shell">
    <aside className={`history ${mobileHistory ? 'history-open' : ''}`}>
      <div className="brand"><span className="brand-mark">L</span><span>LENNY'S<br /><b>GROWTH ASSISTANT</b></span><button className="icon-button mobile-close" aria-label="Close history" onClick={() => setMobileHistory(false)}><X size={17} /></button></div>
      <button className="new-chat" onClick={() => { setSessionId(undefined); setMessages([]); setArtifact(undefined); setMobileHistory(false) }}><Plus size={17} /> New conversation <kbd>⌘ K</kbd></button>
      <div className="history-label">YOUR WORKSPACE</div><button className="history-filter"><span>Recent</span><ChevronDown size={14} /></button>
      <nav className="session-list" aria-label="Conversation history">{sessions.map((session) => <button key={session.id} className={`session-item ${session.id === sessionId ? 'selected' : ''}`} onClick={() => void selectSession(session)}><FileText size={15} /><span>{session.title}</span></button>)}{sessions.length === 0 && <p className="empty-history">Your conversations<br />will show up here.</p>}</nav>
      <div className="sidebar-bottom"><div className="sidebar-note"><BookOpen size={15} /><span>Grounded in conversations<br />with product leaders</span></div><div className="profile"><div className="avatar">Y</div><span>Your workspace</span><ChevronDown size={14} /></div></div>
    </aside>
    {mobileHistory && <button className="scrim" aria-label="Close history" onClick={() => setMobileHistory(false)} />}
    <section className="workspace">
      <header className="topbar"><button className="icon-button mobile-menu" aria-label="Open history" onClick={() => setMobileHistory(true)}><Menu size={19} /></button><div className="breadcrumb">Workspace <span>/</span> <b>Growth assistant</b></div><div className="topbar-right"><span className={`service-status ${health}`}><i />{health === 'online' ? 'API connected' : health === 'checking' ? 'Connecting' : 'API offline'}</span><span className={`service-status ${providerStatuses[model] === 'available' || providerStatuses[model] === 'configured' ? 'online' : providerStatuses[model] === 'checking' ? 'checking' : 'offline'}`} title={`${model === 'ollama' ? 'Ollama' : 'Anthropic'} status`}><i />{model === 'ollama' ? 'Ollama' : 'Anthropic'} {providerStatuses[model].replaceAll('_', ' ')}</span><div className="model-select-wrap"><Sparkles size={14} /><select aria-label="Select language model" value={model} onChange={(event) => setModel(event.target.value as Model)}><option value="ollama">Ollama · Local</option><option value="anthropic">Claude · Cloud</option></select><ChevronDown size={13} /></div></div></header>
      <div className={`work-area ${artifact ? 'with-artifact' : ''}`}>
        <section className="chat-panel" aria-label="Chat"><div className="chat-scroll">
          {messages.length === 0 ? <div className="welcome"><div className="welcome-mark"><Sparkles size={20} /></div><p className="eyebrow">YOUR PRODUCT THINKING PARTNER</p><h1>Good growth starts<br />with a better question.</h1><p className="welcome-copy">Explore the ideas and tactics shared by the world's best product builders.</p><div className="suggestions">{starterQuestions.map((question, index) => <button key={question} className="suggestion" onClick={() => void submit(undefined, question)}><span>0{index + 1}</span>{question}<ArrowUp size={14} /></button>)}</div></div> : <div className="message-list">{messages.map((message, index) => <article key={`${index}-${message.role}`} className={`message ${message.role}`}><div className="message-avatar">{message.role === 'assistant' ? <Sparkles size={14} /> : 'Y'}</div><div className="message-body"><div className="message-role">{message.role === 'assistant' ? 'Lenny assistant' : 'You'}</div><p>{message.content || (loading ? 'Thinking through it…' : '')}</p>{message.citations && message.citations.length > 0 && <div className="citations"><span>FROM THE LIBRARY</span>{message.citations.map((citation, citationIndex) => <a key={`${citation.title}-${citationIndex}`} href={citation.url || '#'} target={citation.url ? '_blank' : undefined} rel="noreferrer"><BookOpen size={13} /><span><b>{citation.title}</b><small>{citation.speaker}{citation.timestamp ? ` · ${citation.timestamp}` : ''}</small></span></a>)}</div>}</div></article>)}{loading && <div className="loading-line"><LoaderCircle size={15} /> Searching the library and shaping a response</div>}</div>}
        </div><div className="composer-wrap"><form className="composer" onSubmit={(event) => void submit(event)}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void submit() } }} placeholder="Ask about product, growth, or how to ship…" rows={2} aria-label="Your message" /><div className="composer-actions"><label className="mode-select-wrap">Mode <select aria-label="Response mode" value={mode} onChange={(event) => setMode(event.target.value as ChatMode)}><option value="quote">Exact source</option><option value="answer">AI answer</option><option value="essay">Ship 30 for 30 essay</option><option value="artifact">Artifact</option></select><ChevronDown size={13} /></label><span>Exact mode quotes indexed sources</span><button type="submit" className="send-button" disabled={!draft.trim() || loading} aria-label="Send message"><ArrowUp size={17} /></button></div></form>{error && <p className="error-message" role="alert">{error}</p>}<p className="disclaimer">AI can make mistakes. Verify important details against the original source.</p></div></section>
        {artifact && <aside className="artifact-panel"><div className="artifact-header"><div><span className="artifact-kicker">WORKING DOCUMENT</span><h2>{artifact.title}</h2></div><button className="icon-button" aria-label="Close artifact" onClick={() => setArtifact(undefined)}><X size={17} /></button></div><div className="artifact-tabs"><span className="active">Preview</span><span>{artifact.type.toUpperCase()}</span><button onClick={() => void navigator.clipboard?.writeText(artifact.content)}><SquarePen size={14} /> Copy</button></div>{artifact.type === 'html' ? <iframe className="artifact-frame" sandbox="" title="Sanitized artifact preview" srcDoc={sanitizePreview(artifact.content)} /> : <pre className="artifact-content">{artifact.content}</pre>}</aside>}
      </div>
    </section>
  </main>
}

async function readChatStream(response: Response, handlers: { onToken: (answer: string, citations: Citation[]) => void; onCitations: (citations: Citation[]) => void }): Promise<Artifact | undefined> {
  if (!response.body) throw new Error('The assistant returned no response stream.')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let answer = ''
  let citations: Citation[] = []
  let artifact: Artifact | undefined

  function processBlock(block: string) {
    const data = block.split('\n').find((line) => line.startsWith('data: '))?.slice(6)
    if (!data) return
    const payload = JSON.parse(data) as { type: string; text?: string; citations?: Citation[]; artifact?: Artifact; message?: string }
    if (payload.type === 'token') {
      answer += payload.text ?? ''
      handlers.onToken(answer, citations)
    } else if (payload.type === 'citations') {
      citations = payload.citations ?? []
      handlers.onCitations(citations)
    } else if (payload.type === 'artifact') artifact = payload.artifact
    else if (payload.type === 'error') throw new Error(payload.message ?? 'Assistant error')
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''
    events.forEach(processBlock)
  }
  buffer += decoder.decode()
  if (buffer.trim()) processBlock(buffer)
  return artifact
}

function sanitizePreview(input: string) {
  const document = new DOMParser().parseFromString(input, 'text/html')
  document.querySelectorAll('script, iframe, object, embed, form, link, meta, base').forEach((element) => element.remove())
  document.querySelectorAll('*').forEach((element) => {
    for (const attribute of [...element.attributes]) if (attribute.name.toLowerCase().startsWith('on') || (['href', 'src', 'action'].includes(attribute.name.toLowerCase()) && /^\s*javascript:/i.test(attribute.value))) element.removeAttribute(attribute.name)
  })
  return `<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src 'none';"><style>body{font:15px/1.65 ui-serif,Georgia,serif;color:#29322f;margin:36px auto;max-width:720px;padding:0 24px}h1,h2,h3{font-family:ui-sans-serif,system-ui}a{color:#1c7465}img{max-width:100%}</style></head><body>${document.body.innerHTML}</body></html>`
}

export default App
