import { useState, useEffect, useRef } from 'react'
import { Input, Button, Card, Spin, message } from 'antd'
import { SendOutlined, UserOutlined, RobotOutlined } from '@ant-design/icons'

const { TextArea } = Input

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

interface ChatResponse {
  message: ChatMessage
  session_id: string
  suggestions: string[]
}

// Use relative API URL (works when frontend and backend are on same origin)
const API_BASE = ''

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load session from localStorage on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem('chat_session_id')
    if (savedSessionId) {
      // Restore chat history
      fetchChatHistory(savedSessionId)
    }
  }, [])

  // Save session_id to localStorage when it changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('chat_session_id', sessionId)
    }
  }, [sessionId])

  const fetchChatHistory = async (sid: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/chat/chat/history/${sid}`)
      if (response.ok) {
        const history = await response.json()
        if (history && history.length > 0) {
          setMessages(history)
          setSessionId(sid)
        }
      }
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }

  const sendMessage = async (content: string) => {
    if (!content.trim()) return

    setLoading(true)

    // Add user message immediately
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: content,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMsg])
    setInputValue('')

    try {
      const response = await fetch(`${API_BASE}/api/chat/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content,
          session_id: sessionId
        })
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data: ChatResponse = await response.json()

      // Update session ID if new
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id)
      }

      // Add assistant message
      setMessages(prev => [...prev, data.message])

      // Update suggestions
      if (data.suggestions && data.suggestions.length > 0) {
        setSuggestions(data.suggestions)
      }
    } catch (error) {
      message.error('发送消息失败，请重试')
      console.error('Chat error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSend = () => {
    sendMessage(inputValue)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion)
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 120px)',
      maxWidth: '800px',
      margin: '0 auto',
      padding: '20px'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#1a1a1a' }}>
          AI 智能投研助手
        </h1>
        <p style={{ color: '#666', marginTop: '8px' }}>
          基于大模型的智能股票分析助手
        </p>
      </div>

      {/* Chat Messages */}
      <Card
        style={{
          flex: 1,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}
        bodyStyle={{
          flex: 1,
          overflow: 'auto',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}
      >
        {messages.length === 0 ? (
          <div style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#999'
          }}>
            <div style={{ textAlign: 'center' }}>
              <RobotOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
              <p>您好！我是智能投研助手</p>
              <p style={{ fontSize: '14px', marginTop: '8px' }}>
                可以帮您：股票筛选 | 股票分析 | 交易信号 | 风险评估
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                alignItems: 'flex-start',
                gap: '12px'
              }}
            >
              {msg.role === 'assistant' && (
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: '#1890ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  flexShrink: 0
                }}>
                  <RobotOutlined />
                </div>
              )}
              <div
                style={{
                  maxWidth: '70%',
                  padding: '12px 16px',
                  borderRadius: '12px',
                  background: msg.role === 'user' ? '#1890ff' : '#f5f5f5',
                  color: msg.role === 'user' ? '#fff' : '#333',
                  whiteSpace: 'pre-wrap',
                  lineHeight: '1.6'
                }}
              >
                {msg.content}
              </div>
              {msg.role === 'user' && (
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: '#52c41a',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  flexShrink: 0
                }}>
                  <UserOutlined />
                </div>
              )}
            </div>
          ))
        )}

        {loading && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: '#1890ff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff'
            }}>
              <RobotOutlined />
            </div>
            <Spin tip="AI思考中..." />
          </div>
        )}

        <div ref={messagesEndRef} />
      </Card>

      {/* Suggestions */}
      {suggestions.length > 0 && !loading && (
        <div style={{
          display: 'flex',
          gap: '8px',
          flexWrap: 'wrap',
          marginTop: '12px'
        }}>
          {suggestions.map((suggestion, idx) => (
            <Button
              key={idx}
              size="small"
              onClick={() => handleSuggestionClick(suggestion)}
              style={{ borderRadius: '16px' }}
            >
              {suggestion}
            </Button>
          ))}
        </div>
      )}

      {/* Input Area */}
      <div style={{
        marginTop: '16px',
        display: 'flex',
        gap: '12px'
      }}>
        <TextArea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="请输入您的问题..."
          autoSize={{ minRows: 1, maxRows: 4 }}
          style={{ flex: 1 }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          loading={loading}
          style={{ height: 'auto' }}
        >
          发送
        </Button>
      </div>
    </div>
  )
}
