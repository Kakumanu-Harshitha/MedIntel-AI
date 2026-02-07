import React, { useState, useRef } from 'react';
import { 
  Send, Mic, Image as ImageIcon, X, Loader2, 
  FileText, Paperclip, Smile, ShieldCheck 
} from 'lucide-react';
import clsx from 'clsx';

const InputArea = ({ onSend, isLoading }) => {
  const [text, setText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [reportFile, setReportFile] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioBlob(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Error accessing microphone:", error);
      alert("Could not access microphone. Please check permissions.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
    }
  };

  const handleReportUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setReportFile(file);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if ((!text.trim() && !audioBlob && !imageFile && !reportFile) || isLoading) return;

    onSend({ text, audioBlob, imageFile, reportFile });
    
    setText('');
    setAudioBlob(null);
    setImageFile(null);
    setReportFile(null);
  };

  return (
    <div className="bg-white/50 backdrop-blur-xl border border-navy-100 p-2 rounded-[2.5rem] shadow-premium sticky bottom-0 z-40 animate-slide-up">
      {/* Preview Area */}
      {(audioBlob || imageFile || reportFile) && (
        <div className="flex gap-3 p-4 mb-2 overflow-x-auto scrollbar-hide">
          {audioBlob && (
            <div className="flex items-center gap-3 bg-brand-50 text-brand-700 px-4 py-2 rounded-2xl text-sm font-bold border border-brand-100 shadow-sm animate-fade-in shrink-0">
              <div className="w-2 h-2 bg-brand-500 rounded-full animate-pulse" />
              <span>Voice Note</span>
              <button onClick={() => setAudioBlob(null)} className="hover:bg-brand-200 p-1 rounded-lg transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          {imageFile && (
            <div className="flex items-center gap-3 bg-teal-50 text-teal-700 px-4 py-2 rounded-2xl text-sm font-bold border border-teal-100 shadow-sm animate-fade-in shrink-0">
              <ImageIcon className="h-4 w-4" />
              <span className="max-w-[120px] truncate">{imageFile.name}</span>
              <button onClick={() => setImageFile(null)} className="hover:bg-teal-200 p-1 rounded-lg transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          {reportFile && (
            <div className="flex items-center gap-3 bg-navy-50 text-navy-700 px-4 py-2 rounded-2xl text-sm font-bold border border-navy-100 shadow-sm animate-fade-in shrink-0">
              <FileText className="h-4 w-4" />
              <span className="max-w-[120px] truncate">{reportFile.name}</span>
              <button onClick={() => setReportFile(null)} className="hover:bg-navy-200 p-1 rounded-lg transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="relative flex items-center gap-2 p-1">
        <div className="flex items-center px-2">
          <label className="p-3 text-navy-400 hover:text-brand-600 hover:bg-brand-50 rounded-2xl cursor-pointer transition-all active:scale-90" title="Upload Image">
            <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
            <ImageIcon className="h-5 w-5" />
          </label>
          
          <label className="p-3 text-navy-400 hover:text-brand-600 hover:bg-brand-50 rounded-2xl cursor-pointer transition-all active:scale-90" title="Upload Report">
            <input type="file" accept="image/*,application/pdf" className="hidden" onChange={handleReportUpload} />
            <FileText className="h-5 w-5" />
          </label>
        </div>

        <div className="flex-1 relative">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Describe your symptoms or ask a question..."
            className="w-full bg-navy-50/50 border border-navy-100/50 rounded-3xl px-6 py-4 pr-12 focus:ring-4 focus:ring-brand-500/5 focus:border-brand-500 focus:bg-white transition-all outline-none text-navy-900 placeholder:text-navy-300 resize-none font-medium leading-relaxed max-h-32 min-h-[56px]"
            rows={1}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <button
            type="button"
            className="absolute right-4 top-1/2 -translate-y-1/2 p-1 text-navy-300 hover:text-brand-600 transition-colors"
          >
            <Smile className="h-5 w-5" />
          </button>
        </div>

        <div className="flex items-center gap-2 pr-1">
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            className={clsx(
              "p-4 rounded-[1.25rem] transition-all duration-300 shadow-lg active:scale-95",
              isRecording 
                ? "bg-red-500 text-white animate-pulse shadow-red-500/20" 
                : "bg-white border border-navy-100 text-navy-400 hover:text-brand-600 hover:border-brand-100"
            )}
            title={isRecording ? "Stop Recording" : "Record Voice"}
          >
            <Mic className="h-5 w-5" />
          </button>

          <button
            type="submit"
            disabled={isLoading || (!text.trim() && !audioBlob && !imageFile && !reportFile)}
            className={clsx(
              "p-4 rounded-[1.25rem] transition-all duration-300 shadow-xl active:scale-95 group",
              (text.trim() || audioBlob || imageFile || reportFile) && !isLoading
                ? "bg-brand-600 text-white shadow-brand-600/20 hover:bg-brand-700" 
                : "bg-navy-50 text-navy-200 cursor-not-allowed"
            )}
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            )}
          </button>
        </div>
      </form>
      
      <div className="flex justify-center items-center gap-4 px-6 py-2 mt-1">
         <p className="text-[10px] font-bold text-navy-300 uppercase tracking-widest flex items-center gap-1.5">
           <ShieldCheck className="h-3 w-3 text-teal-500" />
           Clinical Grade AI
         </p>
         <div className="w-1 h-1 bg-navy-100 rounded-full" />
         <p className="text-[10px] font-bold text-navy-300 uppercase tracking-widest">
           Secure & Private
         </p>
      </div>
    </div>
  );
};

export default InputArea;
