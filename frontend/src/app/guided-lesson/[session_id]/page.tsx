'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { StudySession, ProgrammaticContent } from '@/types/study-types';

interface Message {
  sender_type: 'USER' | 'AI';
  content: string;
  timestamp: string;
}

export default function GuidedLessonPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session_id: paramSessionId } = params;
  const isResuming = searchParams.get('resume') === 'true';

  const [token, setToken] = useState<string | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const [mainSession, setMainSession] = useState<StudySession | null>(null);
  const [guidedLessonSessionId, setGuidedLessonSessionId] = useState<number | null>(null);
  const [chatHistory, setChatHistory] = useState<Message[]>([]);
  const [userMessage, setUserMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSendingMessage, setIsSendingMessage] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  const actionCalled = useRef(false);

  useEffect(() => {
    const storedToken = localStorage.getItem('accessToken');
    if (storedToken) {
      setToken(storedToken);
    } else {
      router.push('/sign-in');
    }
  }, [router]);

  // Effect to fetch mainSession data
  useEffect(() => {
    if (!paramSessionId || !token) {
      return;
    }

    const fetchMainSession = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`${apiUrl}/study/sessions/${paramSessionId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch study session.');
        }

        const data: StudySession = await response.json();
        setMainSession(data);
      } catch (err: any) {
        setError(err.message || 'An unknown error occurred while fetching session data.');
        console.error('Error fetching main session:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMainSession();
  }, [paramSessionId, token, apiUrl]);

  // Effect to start or resume guided lesson once mainSession is available
  useEffect(() => {
    if (!mainSession || !token || actionCalled.current) return;

    const startGuidedLesson = async () => {
      actionCalled.current = true;
      try {
        setIsLoading(true);
        const response = await fetch(`${apiUrl}/guided-lesson/start`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(mainSession),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to start guided lesson.');
        }

        const data = await response.json();
        setGuidedLessonSessionId(data.session_id);
        
        let initialContent = data.message;
        try {
          const parsed = JSON.parse(data.message);
          if (parsed && typeof parsed === 'object' && parsed.text) {
            initialContent = parsed.text;
          } else if (typeof parsed === 'string') {
            initialContent = parsed;
          }
        } catch (e) {
          // Not a JSON string, initialContent is already data.message
        }

        setChatHistory([{ sender_type: 'AI', content: initialContent, timestamp: new Date().toISOString() }]);
      } catch (err: any) {
        setError(err.message || 'An unknown error occurred while starting guided lesson.');
        console.error('Error starting guided lesson:', err);
      } finally {
        setIsLoading(false);
      }
    };

    const fetchHistory = async () => {
      actionCalled.current = true;
      try {
        setIsLoading(true);
        const response = await fetch(`${apiUrl}/guided-lesson/${paramSessionId}/history`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch chat history.');
        }

        const historyData = await response.json();
        setChatHistory(historyData.map((msg: any) => {
          let content = msg.content;
          if (msg.sender_type === 'AI') {
            try {
              const parsed = JSON.parse(msg.content);
              if (parsed && typeof parsed === 'object' && parsed.text) {
                content = parsed.text;
              } else if (typeof parsed === 'string') {
                content = parsed;
              }
            } catch (e) {
              // Not a JSON string, use content as is
            }
          }
          return {
            sender_type: msg.sender_type,
            content: content,
            timestamp: msg.timestamp,
          };
        }));
        setGuidedLessonSessionId(parseInt(paramSessionId as string, 10));
      } catch (err: any) {
        setError(err.message || 'An unknown error occurred while fetching history.');
        console.error('Error fetching history:', err);
      } finally {
        setIsLoading(false);
      }
    };

    if (isResuming) {
      fetchHistory();
    } else {
      startGuidedLesson();
    }
  }, [mainSession, token, apiUrl, isResuming, paramSessionId]);

  // Scroll to bottom of chat history
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory]);

  const handleSendMessage = async () => {
    if (!userMessage.trim() || !guidedLessonSessionId || !mainSession || !token) return;

    const newUserMessage: Message = {
      sender_type: 'USER',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };
    setChatHistory((prev) => [...prev, newUserMessage]);
    setUserMessage('');
    setIsSendingMessage(true);

    try {
      const response = await fetch(`${apiUrl}/guided-lesson/${guidedLessonSessionId}/chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: userMessage,
          session_contents: mainSession, // Send the original mainSession data as context
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send message.');
      }

      const data = await response.json();
      setChatHistory(data.history.map((msg: any) => {
        let content = msg.content;
        if (msg.sender_type === 'AI') {
          try {
            const parsed = JSON.parse(msg.content);
            if (parsed && typeof parsed === 'object' && parsed.text) {
              content = parsed.text;
            } else if (typeof parsed === 'string') {
              content = parsed;
            }
          } catch (e) {
            // Not a JSON string, use content as is
          }
        }
        return {
          sender_type: msg.sender_type,
          content: content,
          timestamp: msg.timestamp,
        };
      }));
    } catch (err: any) {
      setError(err.message || 'An unknown error occurred while sending message.');
      console.error('Error sending message:', err);
      // Restore user message on error
      setChatHistory((prev) => prev.slice(0, -1));
      setUserMessage(newUserMessage.content);
    } finally {
      setIsSendingMessage(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-gray-500">Loading guided lesson...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-red-500">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <header className="bg-white shadow-sm p-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Guided Lesson: Session #{mainSession?.session_number}</h1>
        <Button onClick={() => router.back()} variant="outline">Back to Dashboard</Button>
      </header>

      <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {chatHistory.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.sender_type === 'USER' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg shadow ${msg.sender_type === 'USER'
                ? 'bg-blue-500 text-white' : 'bg-white text-gray-800'}`}
            >
              {msg.sender_type === 'AI' ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              ) : (
                <p>{msg.content}</p>
              )}
              <span className="block text-xs mt-1 opacity-75">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white p-4 border-t border-gray-200 flex items-center space-x-2">
        <Input
          type="text"
          value={userMessage}
          onChange={(e) => setUserMessage(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              handleSendMessage();
            }
          }}
          placeholder="Type your message..."
          className="flex-1"
          disabled={isSendingMessage}
        />
        <Button onClick={handleSendMessage} disabled={isSendingMessage || !userMessage.trim()}>
          {isSendingMessage ? 'Sending...' : 'Send'}
        </Button>
      </div>
    </div>
  );
}