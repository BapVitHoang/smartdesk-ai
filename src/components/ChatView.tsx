import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  AlertTriangle, 
  BookOpen, 
  ExternalLink, 
  ThumbsUp, 
  ThumbsDown, 
  ArrowRight,
  Sparkles,
  Search
} from 'lucide-react';
import { ChatMessage, TabType, ToastType } from '../types';
import { getRagResponse } from '../data';
import { sendChatMessage } from '../services/api';

interface ChatViewProps {
  chatMessages: ChatMessage[];
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  setActiveTab: (tab: TabType) => void;
  onToast: (msg: string, type?: ToastType) => void;
}

export const ChatView: React.FC<ChatViewProps> = ({
  chatMessages,
  setChatMessages,
  setActiveTab,
  onToast,
}) => {
  const [chatInput, setChatInput] = useState('');
  const [isBotTyping, setIsBotTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isBotTyping]);

  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isBotTyping) return;

    const userText = chatInput.trim();
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: userText,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput('');
    setIsBotTyping(true);

    try {
      const ragAnswer = await sendChatMessage(userText, undefined, onToast);
      const botReply: ChatMessage = {
        id: `bot-${Date.now()}`,
        sender: 'bot',
        text: ragAnswer.response,
        bulletPoints: ragAnswer.bulletPoints,
        citations: ragAnswer.citations,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        feedbackGiven: null,
        latency_ms: ragAnswer.latency_ms,
        confidence: ragAnswer.confidence,
        is_fallback: ragAnswer.is_fallback,
        escalation_recommended: ragAnswer.escalation_recommended,
      };
      setChatMessages((prev) => [...prev, botReply]);
    } catch (err) {
      const fallbackAns = getRagResponse(userText);
      const botReply: ChatMessage = {
        id: `bot-${Date.now()}`,
        sender: 'bot',
        text: fallbackAns.text,
        bulletPoints: fallbackAns.bulletPoints,
        citations: fallbackAns.citations,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        feedbackGiven: null,
        is_fallback: true,
      };
      setChatMessages((prev) => [...prev, botReply]);
    } finally {
      setIsBotTyping(false);
    }
  };

  const handleFeedback = (index: number, type: 'thumb_up' | 'thumb_down') => {
    setChatMessages((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], feedbackGiven: type };
      return next;
    });
    onToast(
      type === 'thumb_up'
        ? 'Cảm ơn đánh giá tích cực của bạn!'
        : 'Đã ghi nhận phản hồi để hoàn thiện mô hình RAG.'
    );
  };

  return (
    <div id="screen-chatbot" className="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-6 flex flex-col h-full overflow-hidden">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-xs flex flex-col flex-1 overflow-hidden">
        
        {/* Chat Header */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold shadow-md shadow-indigo-100">
                <Bot className="w-5 h-5" />
              </div>
              <span className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-emerald-500 border-2 border-white rounded-full"></span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-slate-800 text-sm sm:text-base">SmartDesk RAG Assistant</h2>
                <span className="bg-indigo-100 text-indigo-700 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                  v3.2 Hybrid Search
                </span>
              </div>
              <p className="text-xs text-slate-500">Tra cứu tự động từ hơn 500+ tài liệu nội bộ và quy trình chuẩn</p>
            </div>
          </div>

          <button
            id="btn-escalate-from-chat"
            onClick={() => setActiveTab('ticket')}
            className="hidden sm:flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300/80 font-medium text-xs transition-colors shadow-xs"
          >
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>Gặp sự cố? Chuyển sang gửi Ticket</span>
          </button>
        </div>

        {/* Chat Messages List */}
        <div id="chat-messages-container" className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 custom-scrollbar bg-slate-50/40">
          {chatMessages.map((msg, idx) => (
            <div
              key={msg.id || idx}
              className={`flex gap-3 max-w-3xl ${msg.sender === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 shadow-xs ${
                  msg.sender === 'user' ? 'bg-slate-800 text-white' : 'bg-indigo-600 text-white'
                }`}
              >
                {msg.sender === 'user' ? 'ME' : 'AI'}
              </div>

              <div
                className={`rounded-2xl p-4 text-sm shadow-xs ${
                  msg.sender === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none space-y-3'
                }`}
              >
                {msg.is_fallback && (
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-50 border border-amber-300/80 text-amber-800 text-xs font-semibold w-fit">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span>Chế độ Dự phòng (Deterministic Fallback Active)</span>
                  </div>
                )}

                <div className="leading-relaxed font-normal">{msg.text}</div>

                {msg.bulletPoints && msg.bulletPoints.length > 0 && (
                  <ul className="space-y-1.5 my-2 pl-4 list-disc text-slate-700 text-xs sm:text-sm">
                    {msg.bulletPoints.map((item, bIdx) => (
                      <li key={bIdx} className="leading-relaxed">
                        {item}
                      </li>
                    ))}
                  </ul>
                )}

                {msg.citations && msg.citations.length > 0 && (
                  <div className="pt-2.5 border-t border-slate-100">
                    <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
                      <span>Trích dẫn tài liệu tham chiếu (RAG Citations):</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.citations.map((cite, cIdx) => (
                        <span
                          key={cIdx}
                          onClick={() => onToast(`Đang mở tài liệu: ${cite.code}`, 'info')}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-medium border border-indigo-200/70 cursor-pointer transition-colors"
                          title={cite.title || cite.code}
                        >
                          <ExternalLink className="w-3 h-3 text-indigo-500 shrink-0" />
                          <span>[{cite.code}]</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {msg.escalation_recommended && (
                  <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>Câu hỏi cần hỗ trợ chuyên sâu. Khuyến nghị tạo phiếu hỗ trợ kỹ thuật:</span>
                    </div>
                    <button
                      onClick={() => setActiveTab('ticket')}
                      className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-lg text-xs shrink-0 shadow-xs transition-colors"
                    >
                      Gửi Ticket ngay
                    </button>
                  </div>
                )}

                {msg.sender === 'bot' && (
                  <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                    <div className="flex items-center gap-2">
                      <span>Was this helpful?</span>
                      <button
                        onClick={() => handleFeedback(idx, 'thumb_up')}
                        className={`p-1.5 rounded-md hover:bg-slate-100 transition-colors flex items-center gap-1 ${
                          msg.feedbackGiven === 'thumb_up' ? 'bg-emerald-100 text-emerald-700 font-bold' : ''
                        }`}
                        title="Hữu ích"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                        <span>Có</span>
                      </button>
                      <button
                        onClick={() => handleFeedback(idx, 'thumb_down')}
                        className={`p-1.5 rounded-md hover:bg-slate-100 transition-colors flex items-center gap-1 ${
                          msg.feedbackGiven === 'thumb_down' ? 'bg-rose-100 text-rose-700 font-bold' : ''
                        }`}
                        title="Chưa hữu ích"
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                        <span>Chưa</span>
                      </button>
                    </div>

                    <button
                      onClick={() => setActiveTab('ticket')}
                      className="text-indigo-600 hover:text-indigo-800 font-medium underline inline-flex items-center gap-1"
                    >
                      <span>Chưa giải quyết được? Gửi Ticket ngay</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}

                <div
                  className={`text-[10px] mt-1 flex items-center justify-between gap-2 ${
                    msg.sender === 'user' ? 'text-indigo-200 text-right' : 'text-slate-400'
                  }`}
                >
                  {msg.sender === 'bot' && msg.latency_ms !== undefined ? (
                    <div className="flex items-center gap-2 font-mono">
                      <span>⚡ {msg.latency_ms}ms</span>
                      {msg.confidence !== undefined && (
                        <span>• Tin cậy: {(msg.confidence * 100).toFixed(0)}%</span>
                      )}
                    </div>
                  ) : (
                    <span />
                  )}
                  <span>{msg.time}</span>
                </div>
              </div>
            </div>
          ))}

          {isBotTyping && (
            <div className="flex gap-3 max-w-md">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center text-xs font-bold shrink-0">
                AI
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none p-3.5 text-xs text-slate-500 flex items-center gap-2 shadow-xs">
                <span className="w-2 h-2 rounded-full bg-indigo-600 animate-ping"></span>
                <span>Đang tra cứu Vector Database và tổng hợp trích dẫn...</span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Suggestion Chips */}
        <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 flex items-center gap-2 overflow-x-auto text-xs text-slate-600">
          <span className="font-semibold text-slate-400 shrink-0 text-[11px] flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-indigo-500" />
            Gợi ý câu hỏi:
          </span>
          <button
            type="button"
            onClick={() => setChatInput('Chính sách hoàn tiền khi thanh toán bị trừ 2 lần?')}
            className="px-2.5 py-1 bg-white hover:bg-indigo-50 hover:text-indigo-700 rounded-lg border border-slate-200 shrink-0 text-slate-700 transition-colors"
          >
            💳 Hoàn tiền lỗi giao dịch
          </button>
          <button
            type="button"
            onClick={() => setChatInput('Cách tạo API Token để tích hợp webhook?')}
            className="px-2.5 py-1 bg-white hover:bg-indigo-50 hover:text-indigo-700 rounded-lg border border-slate-200 shrink-0 text-slate-700 transition-colors"
          >
            🔑 Cấp API Key mới
          </button>
          <button
            type="button"
            onClick={() => setChatInput('Thời gian phản hồi SLA của gói Pro là bao lâu?')}
            className="px-2.5 py-1 bg-white hover:bg-indigo-50 hover:text-indigo-700 rounded-lg border border-slate-200 shrink-0 text-slate-700 transition-colors"
          >
            ⏱️ SLA cam kết hỗ trợ
          </button>
        </div>

        {/* Chat Input Bar */}
        <form onSubmit={handleSendChat} className="p-3 sm:p-4 bg-white border-t border-slate-200 flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              id="chat-query-input"
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Nhập câu hỏi cần tra cứu tài liệu hỗ trợ (vd: lỗi 2FA, thanh toán, export)..."
              className="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all text-slate-800 placeholder:text-slate-400"
            />
          </div>
          <button
            id="chat-submit-button"
            type="submit"
            disabled={!chatInput.trim() || isBotTyping}
            className={`px-5 py-2.5 rounded-xl font-medium text-sm flex items-center gap-2 transition-all ${
              !chatInput.trim() || isBotTyping
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md shadow-indigo-100 active:scale-95'
            }`}
          >
            <span>Gửi</span>
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
