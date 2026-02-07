import React, { useState, useEffect, useRef } from 'react';
import Header from '../components/Header';
import InputArea from '../components/InputArea';
import ReportCard from '../components/ReportCard';
import { dashboardService, queryService } from '../services/api';
import { Loader2, User, Bot, Trash2, HeartPulse, Sparkles, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

const Chat = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);
  const scrollRef = useRef(null);

  const fetchHistory = async () => {
    try {
      const data = await dashboardService.getHistory();
      setHistory(data);
    } catch (error) {
      console.error("Failed to fetch history:", error);
    } finally {
      setInitialLoad(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [history]);

  const handleSend = async ({ text, audioBlob, imageFile, reportFile }) => {
    let contentParts = [];
    if (text) contentParts.push(text);
    if (audioBlob) contentParts.push('🎤 Voice Message');
    if (imageFile) contentParts.push('📷 Image Upload (Physical)');
    if (reportFile) contentParts.push('📄 Medical Report Upload');

    const content = contentParts.join(' + ') || 'New Assessment';

    const userMsg = {
      role: 'user',
      content: content
    };
    setHistory(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await queryService.sendMultimodalQuery(text, audioBlob, imageFile, reportFile);
      
      const aiMsg = {
        role: 'assistant',
        content: response.text_response,
        audio_url: response.audio_url
      };
      setHistory(prev => [...prev, aiMsg]);
    } catch (error) {
      console.error("Error sending query:", error);
      const errorMsg = {
        role: 'assistant',
        content: JSON.stringify({
          summary: "Error processing request.",
          severity: "UNKNOWN",
          analysis: "Something went wrong. Please try again.",
          disclaimer: "System Error"
        })
      };
      setHistory(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = async () => {
    if (!window.confirm("Are you sure you want to clear all chat history? This cannot be undone.")) return;
    try {
      await dashboardService.clearHistory();
      setHistory([]);
    } catch (error) {
      console.error("Failed to clear history:", error);
      alert("Failed to clear history. Please try again.");
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-brand-50 via-white to-navy-50 flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-6 flex flex-col relative overflow-hidden">
        {history.length > 0 && (
          <div className="flex justify-between items-center mb-6 animate-fade-in">
             <div className="flex items-center gap-2 text-navy-400 text-xs font-bold uppercase tracking-widest">
                <Sparkles className="h-3 w-3 text-brand-500" />
                Live Assessment Session
             </div>
             <button 
                onClick={handleClearChat}
                className="group flex items-center gap-2 px-3 py-1.5 rounded-xl text-navy-400 hover:text-red-600 hover:bg-red-50 transition-all border border-transparent hover:border-red-100"
                title="Clear Chat History"
              >
                <Trash2 className="h-4 w-4 group-hover:rotate-12 transition-transform" />
                <span className="text-xs font-bold">Reset</span>
              </button>
          </div>
        )}

        {initialLoad ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 animate-pulse-soft">
            <div className="p-4 bg-brand-50 rounded-3xl">
               <Loader2 className="h-8 w-8 animate-spin text-brand-600" />
            </div>
            <p className="text-navy-400 font-bold text-sm uppercase tracking-widest">Loading Records...</p>
          </div>
        ) : (
          <div className="flex-1 space-y-8 mb-4 overflow-y-auto pr-2 custom-scrollbar">
            {history.length === 0 && (
              <div className="flex-1 flex flex-col items-center justify-center py-20 animate-slide-up">
                <div className="w-24 h-24 bg-gradient-to-br from-brand-600 to-brand-500 rounded-[2rem] flex items-center justify-center mb-8 shadow-2xl shadow-brand-600/20 rotate-3">
                  <HeartPulse className="h-12 w-12 text-white" />
                </div>
                <h3 className="text-3xl font-extrabold text-navy-900 tracking-tight text-center">
                   How can I help you <br />
                   <span className="text-brand-600">today?</span>
                </h3>
                <p className="text-navy-400 mt-4 text-center max-w-xs leading-relaxed font-medium">
                  Describe your symptoms, upload a report, or send a voice note for an instant AI assessment.
                </p>
                
                <div className="grid grid-cols-2 gap-3 mt-12 w-full max-w-md">
                   <div className="p-4 rounded-2xl bg-white border border-navy-100 shadow-premium text-center">
                      <div className="text-brand-600 font-bold text-sm mb-1">Instant</div>
                      <div className="text-navy-900 font-bold">Symptom Check</div>
                   </div>
                   <div className="p-4 rounded-2xl bg-white border border-navy-100 shadow-premium text-center">
                      <div className="text-teal-600 font-bold text-sm mb-1">Deep</div>
                      <div className="text-navy-900 font-bold">Report Analysis</div>
                   </div>
                </div>
              </div>
            )}

            {history.map((msg, idx) => (
              <div key={idx} className={clsx(
                "flex gap-4 group animate-fade-in",
                msg.role === 'user' ? 'flex-row-reverse' : ''
              )}>
                <div className={clsx(
                  "w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-lg transition-transform group-hover:scale-110",
                  msg.role === 'user' 
                    ? 'bg-navy-900 text-white rotate-3' 
                    : 'bg-white border border-navy-100 text-brand-600 -rotate-3'
                )}>
                  {msg.role === 'user' ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
                </div>
                <div className={clsx(
                  "flex-1 flex",
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                )}>
                  {msg.role === 'user' ? (
                    <div className="bg-navy-900 text-white px-6 py-4 rounded-3xl rounded-tr-sm max-w-[85%] shadow-xl shadow-navy-900/10">
                      <p className="whitespace-pre-wrap leading-relaxed font-medium text-[15px]">{msg.content}</p>
                    </div>
                  ) : (
                    <div className="w-full max-w-[95%]">
                      <ReportCard data={msg.content} audioUrl={msg.audio_url} />
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {loading && (
              <div className="flex gap-4 animate-fade-in">
                 <div className="w-10 h-10 rounded-2xl bg-white border border-navy-100 flex items-center justify-center text-brand-600 shrink-0 shadow-md -rotate-3">
                  <Bot className="h-5 w-5" />
                </div>
                <div className="bg-white rounded-2xl px-6 py-4 border border-navy-100 shadow-premium flex items-center gap-4">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-brand-600 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                    <div className="w-2 h-2 bg-brand-600 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                    <div className="w-2 h-2 bg-brand-600 rounded-full animate-bounce"></div>
                  </div>
                  <span className="text-sm font-bold text-navy-400 uppercase tracking-widest">AI is thinking...</span>
                </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        )}
      </main>

      <div className="max-w-4xl w-full mx-auto px-4 pb-6">
        <InputArea onSend={handleSend} isLoading={loading} />
      </div>
    </div>
  );
};

export default Chat;
