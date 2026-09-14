import React, { useEffect, useState } from 'react';
import { MessageCircle, MessageCircleQuestion, Send, Crosshair, X, Minus } from 'lucide-react';
import { askQuestion } from '../services/comparisonService';
import { ChangeItem } from '../types/comparison';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  referencedChangeIds?: string[];
}

interface QaChatPanelProps {
  reportId?: string;
  changes: ChangeItem[];
  onSelectChange: (changeId: string) => void;
}

/**
 * Floating AI chat widget (customer-support style).
 * Fixed to the viewport bottom-right: a small icon by default, expanding to
 * an overlay panel on click. Overlay only — never affects page layout.
 */
export const QaChatPanel: React.FC<QaChatPanelProps> = ({ reportId, changes, onSelectChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [isOpen]);

  // Reset conversation when the underlying report changes.
  useEffect(() => {
    setMessages([]);
    setError(null);
    setInput('');
  }, [reportId]);

  const send = async () => {
    const question = input.trim();
    if (!question || busy) return;
    if (!reportId) {
      setError('This comparison has no persisted report yet, so questions cannot be answered.');
      return;
    }
    setError(null);
    setBusy(true);
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setInput('');
    try {
      const answer = await askQuestion(reportId, question);
      const referencedChangeIds = (answer.referenced_change_indices ?? [])
        .map((i) => changes[i]?.id)
        .filter((id): id is string => Boolean(id));
      setMessages((prev) => [...prev, { role: 'assistant', text: answer.answer, referencedChangeIds }]);
    } catch (err: any) {
      setError(err?.message || 'Could not answer that question.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {/* Floating button — always visible, fixed to viewport */}
      {!isOpen && (
        <button
          id="btn-open-ai-chat"
          onClick={() => setIsOpen(true)}
          title="Ask AI about these changes"
          aria-label="Open AI chat"
          className="fixed bottom-5 right-5 sm:bottom-6 sm:right-6 z-50 w-12 h-12 rounded-full bg-cyprus hover:bg-cyprus-deep text-white shadow-lg flex items-center justify-center transition-colors cursor-pointer"
        >
          <MessageCircle className="w-5 h-5" />
        </button>
      )}

      {/* Chat panel — fixed overlay, never shifts page layout */}
      {isOpen && (
        <div
          id="ai-chat-panel"
          role="dialog"
          aria-label="AI chat"
          className="fixed bottom-5 right-5 sm:bottom-6 sm:right-6 z-50 w-[min(22rem,calc(100vw-2.5rem))] h-[min(40rem,calc(100vh-7rem))] min-h-[22rem] bg-white border border-cyprus/20 rounded-[14px] shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="px-4 py-3 bg-[#FAFAFA] border-b border-[#E5E5E5] flex items-center justify-between gap-2 shrink-0">
            <span className="inline-flex items-center gap-2">
              <MessageCircleQuestion className="w-4 h-4 text-[#0A0A0A]" />
              <span className="text-sm font-semibold text-[#0A0A0A] tracking-tight">Ask AI</span>
              <span className="text-[11px] font-mono text-[#6b7280] hidden sm:inline">grounded in detected deltas</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <button
                onClick={() => setIsOpen(false)}
                title="Minimize chat"
                aria-label="Minimize chat"
                className="p-1.5 rounded-[8px] text-[#A3A3A3] hover:text-[#0A0A0A] hover:bg-white border border-transparent hover:border-[#E5E5E5] transition-colors cursor-pointer"
              >
                <Minus className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Close chat"
                aria-label="Close chat"
                className="p-1.5 rounded-[8px] text-[#A3A3A3] hover:text-[#0A0A0A] hover:bg-white border border-transparent hover:border-[#E5E5E5] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </span>
          </div>

          {/* Conversation */}
          <div className="px-4 py-3 space-y-2.5 overflow-y-auto flex-1 min-h-0">
            {messages.length === 0 && !busy && (
              <div className="h-full min-h-40 flex items-center justify-center">
                <p className="text-[13px] text-[#6b7280] font-mono">Start a conversation</p>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[90%] rounded-[10px] px-3 py-2 text-[13px] leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-[#0A0A0A] text-white'
                      : 'bg-[#FAFAFA] border border-[#E5E5E5] text-[#0A0A0A]'
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{m.text}</p>
                  {m.role === 'assistant' && m.referencedChangeIds && m.referencedChangeIds.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {m.referencedChangeIds.map((id) => (
                        <button
                          key={id}
                          onClick={() => onSelectChange(id)}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[6px] bg-white border border-[#E5E5E5] text-[11px] font-mono text-[#525252] hover:text-[#0A0A0A] hover:border-[#0A0A0A] transition-colors cursor-pointer"
                        >
                          {id}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && <p className="text-xs font-mono text-[#A3A3A3] animate-pulse">Thinking…</p>}
          </div>

          {error && <p className="px-4 pb-1 text-xs font-mono text-rose-700">{error}</p>}

          {/* Input */}
          <div className="px-3 py-3 border-t border-[#E5E5E5] bg-white flex items-center gap-2 shrink-0">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') send();
              }}
              placeholder="Ask about the detected changes…"
              disabled={busy}
              className="flex-1 min-w-0 px-3 py-2 text-[13px] bg-[#FAFAFA] border border-[#E5E5E5] rounded-[8px] focus:bg-white focus:outline-none focus:border-[#0A0A0A] text-[#0A0A0A] placeholder-[#6b7280]"
            />
            <button
              onClick={send}
              disabled={busy || !input.trim()}
              aria-label="Send message"
              className="shrink-0 inline-flex items-center justify-center w-9 h-9 bg-cyprus hover:bg-cyprus-deep disabled:opacity-50 text-white rounded-full transition-colors cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </>
  );
};
