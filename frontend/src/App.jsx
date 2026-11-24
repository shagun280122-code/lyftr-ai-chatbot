
import { useEffect, useRef, useState } from 'react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [sessionId] = useState(() => crypto.randomUUID())
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hello! I'm Lyftr AI. How can I help you today?"
    }
  ])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendMessage(e) {
    e.preventDefault()

    const text = message.trim()
    if (!text || loading) return

    setError('')
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setMessage('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          system_prompt: 'You are Lyftr AI, a helpful, friendly and clear AI assistant.'
        })
      })

      if (!response.ok) {
        const details = await response.text()
        throw new Error(details || `Server error: ${response.status}`)
      }

      const data = await response.json()

      const reply =
        data.response ??
        data.reply ??
        data.message ??
        data.content

      if (typeof reply !== 'string') {
        throw new Error('Unexpected API response. Please check the backend response format.')
      }

      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: reply }
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">✦</span>
          <span>lyftr<span className="brand-light">.ai</span></span>
        </div>

        <button className="new-chat" onClick={() => window.location.reload()}>
          + New chat
        </button>

        <div className="sidebar-bottom">
          <div className="profile-icon">L</div>
          <div>
            <strong>Lyftr AI</strong>
            <small>AI Assistant</small>
          </div>
        </div>
      </aside>

      <section className="chat-area">
        <header className="topbar">
          <div>
            <strong>AI Assistant</strong>
            <span className="online-dot">● Online</span>
          </div>
          <span className="model-label">Powered by AI</span>
        </header>

        <div className="messages">
          <div className="welcome">
            <div className="welcome-icon">✦</div>
            <h1>How can I help you?</h1>
            <p>Ask anything. Let's figure it out together.</p>
          </div>

          {messages.slice(1).map((msg, index) => (
            <div className={`message-row ${msg.role}`} key={index}>
              <div className="avatar">
                {msg.role === 'user' ? 'Y' : '✦'}
              </div>
              <div className="message-content">
                <strong>{msg.role === 'user' ? 'You' : 'Lyftr AI'}</strong>
                <p>{msg.content}</p>
              </div>
            </div>
          ))}

          {loading && (
            <div className="message-row assistant">
              <div className="avatar">✦</div>
              <div className="typing">Lyftr AI is thinking...</div>
            </div>
          )}

          {error && <div className="error">{error}</div>}
          <div ref={bottomRef} />
        </div>

        <div className="composer-wrap">
          <form className="composer" onSubmit={sendMessage}>
            <textarea
              value={message}
              onChange={e => setMessage(e.target.value)}
              placeholder="Message Lyftr AI..."
              rows="1"
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage(e)
                }
              }}
            />
            <button type="submit" disabled={!message.trim() || loading}>
              ↑
            </button>
          </form>
          <small>Lyftr AI can make mistakes. Verify important information.</small>
        </div>
      </section>
    </main>
  )
}

export default App
