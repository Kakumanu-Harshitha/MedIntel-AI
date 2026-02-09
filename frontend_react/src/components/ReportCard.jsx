import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle2, AlertOctagon, Info, Stethoscope, Utensils, Activity, Download, FileText, Brain, ShieldCheck, ThumbsUp, ThumbsDown, HelpCircle, Volume2, User as UserIcon, Image as ImageIcon, AlertCircle, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import { dashboardService, feedbackService } from '../services/api';
import FeedbackModal from './FeedbackModal';

const SeverityBadge = ({ level }) => {
  const configs = {
    LOW: { color: "bg-emerald-50 text-emerald-700 border-emerald-100", icon: ShieldCheck },
    MODERATE: { color: "bg-amber-50 text-amber-700 border-amber-100", icon: AlertCircle },
    HIGH: { color: "bg-orange-50 text-orange-700 border-orange-100", icon: AlertTriangle },
    EMERGENCY: { color: "bg-rose-50 text-rose-700 border-rose-100 animate-pulse", icon: AlertOctagon },
    UNKNOWN: { color: "bg-slate-50 text-slate-700 border-slate-100", icon: Info }
  };

  const config = configs[level] || configs.UNKNOWN;
  const Icon = config.icon || Info;

  return (
    <span className={clsx(
      "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold border uppercase tracking-wider shadow-sm",
      config.color
    )}>
      <Icon size={12} className="shrink-0" />
      {level}
    </span>
  );
};

const ConfidenceBar = ({ score, reason }) => {
  let percentage = 0;
  if (typeof score === 'number') {
    percentage = Math.round(score * 100);
  } else if (typeof score === 'string') {
    const s = score.toLowerCase();
    if (s.includes('high')) percentage = 92;
    else if (s.includes('medium')) percentage = 65;
    else if (s.includes('low')) percentage = 35;
  }

  const color = percentage > 85 ? "bg-emerald-500" : percentage > 60 ? "bg-brand-500" : "bg-orange-500";

  return (
    <div className="flex flex-col gap-2 w-full max-w-sm">
      <div className="flex justify-between items-end">
        <div className="flex flex-col">
          <span className="text-[10px] font-bold text-navy-400 uppercase tracking-widest mb-0.5">AI Precision</span>
          {reason && <span className="text-[10px] text-navy-300 italic font-medium leading-tight max-w-[200px]">{reason}</span>}
        </div>
        <span className={clsx("text-sm font-black tabular-nums", color.replace('bg-', 'text-'))}>{percentage}%</span>
      </div>
      <div className="h-2.5 w-full bg-navy-50/50 rounded-full overflow-hidden border border-navy-100/30 p-0.5">
        <div 
          className={clsx("h-full transition-all duration-1000 ease-out rounded-full shadow-sm", color)}
          style={{ width: `${percentage}%` }} 
        />
      </div>
    </div>
  );
};

const FeedbackSection = ({ feedbackGiven, onFeedback, onNegativeClick }) => {
  if (feedbackGiven) {
    return (
      <div className="px-6 py-3 bg-navy-50/20 flex items-center justify-end gap-3 border-t border-navy-50/50 animate-fade-in">
        <div className="flex items-center gap-2 text-emerald-600 font-bold text-[10px] uppercase tracking-widest">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Thank you for your feedback!
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-3 bg-navy-50/20 border-t border-navy-50/50">
      <div className="flex items-center justify-end gap-3">
        <span className="text-[9px] font-black text-navy-400 uppercase tracking-widest">Helpful?</span>
        <div className="flex items-center gap-2">
          <button 
              onClick={() => onFeedback('positive')}
              className="p-2 rounded-lg transition-all border shadow-sm active:scale-90 bg-white text-navy-400 hover:text-emerald-500 hover:border-emerald-200"
          >
              <ThumbsUp className="h-3.5 w-3.5" />
          </button>
          <button 
              onClick={onNegativeClick}
              className="p-2 rounded-lg transition-all border shadow-sm active:scale-90 bg-white text-navy-400 hover:text-rose-500 hover:border-rose-200"
          >
              <ThumbsDown className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};

const ReportCard = ({ data, report: reportProp, audioUrl, reportId }) => {
  const [downloading, setDownloading] = useState(false);
  const [showExplanation, setShowExplanation] = useState(false);
  
  // Safe Parsing
  const initialData = reportProp || data;
  let report = initialData;
  
  // If initialData is a message object from MongoDB (has content field)
  if (initialData && typeof initialData === 'object' && 'content' in initialData) {
    const content = initialData.content;
    if (typeof content === 'string') {
      try {
        report = JSON.parse(content);
      } catch (e) {
        report = content;
      }
    } else {
      report = content;
    }
    // Carry over metadata from the message object
    if (typeof report === 'object' && report !== null) {
      if (initialData.feedback_rating) report.feedback_rating = initialData.feedback_rating;
      if (initialData.patient_name) report.patient_name = initialData.patient_name;
      if (initialData.isLatest) report.isLatest = initialData.isLatest;
    }
  } else if (typeof initialData === 'string') {
    try {
      report = JSON.parse(initialData);
    } catch (e) {
      // If it's not JSON, we'll handle it as plain text later
    }
  }

  // Initialize feedbackGiven from the report data (which now includes feedback_rating from backend)
  const [feedbackGiven, setFeedbackGiven] = useState(null);

  useEffect(() => {
    if (report?.feedback_rating) {
      setFeedbackGiven(report.feedback_rating);
    } else if (initialData?.feedback_rating) {
      setFeedbackGiven(initialData.feedback_rating);
    }
  }, [report, initialData]);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleFeedback = async (rating, comment = null) => {
    if (feedbackGiven) return;
    setFeedbackGiven(rating);
    try {
        // Use the already parsed 'report' object for context
        const context = typeof report === 'string' ? report : report?.summary || report?.health_information || "No summary available";
        await feedbackService.submitFeedback(rating, context, reportId, comment);
        
        if (rating === 'positive') {
          toast.success('Thank you for your valuable feedback!', {
            style: {
              borderRadius: '12px',
              background: '#0F172A',
              color: '#fff',
              fontSize: '12px',
              fontWeight: 'bold',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            },
          });
        } else {
          toast.success('Thanks! Your feedback helps us improve.', {
            style: {
              borderRadius: '12px',
              background: '#0F172A',
              color: '#fff',
              fontSize: '12px',
              fontWeight: 'bold',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            },
          });
        }
    } catch (e) {
        console.error("Feedback error", e);
        toast.error('Failed to submit feedback.');
    }
  };

  const handleNegativeSubmit = async (reason, text) => {
    const fullComment = text ? `${reason}: ${text}` : reason;
    await handleFeedback('negative', fullComment);
  };

  const handleDownload = async () => {
    try {
      setDownloading(true);
      const email = localStorage.getItem('email');
      if (!email) {
        alert("Please log in to download reports.");
        return;
      }
      
      const blob = await dashboardService.getReportPdf(email, reportId);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `HealthReport_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (error) {
      console.error("Download failed", error);
      alert("Failed to download report. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  // Handle Chat Message (Small Talk)
  if (report?.type === 'chat_message') {
    return (
      <div className="bg-white rounded-3xl p-6 shadow-premium border border-navy-100 animate-fade-in max-w-xl prose prose-sm prose-navy">
        <ReactMarkdown>{report.message}</ReactMarkdown>
      </div>
    );
  }

  // Handle plain text (if parsing failed and it's not a structured report)
  if (typeof report === 'string') {
    return (
      <div className="bg-white rounded-3xl p-8 shadow-premium border border-navy-100 animate-fade-in prose prose-navy">
        <ReactMarkdown>{report}</ReactMarkdown>
      </div>
    );
  }

  // Handle General Health Report (Symptom Analysis)
  if (report?.type === 'health_report') {
    return (
      <div className="bg-white rounded-2xl shadow-premium border border-navy-100/60 overflow-hidden max-w-xl animate-slide-up hover:shadow-xl transition-all duration-500">
        {audioUrl && (
          <div className="px-5 pt-5">
            <div className="bg-navy-50/50 rounded-xl p-2.5 flex items-center gap-3 border border-navy-100/40 backdrop-blur-sm">
                 <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center text-white shadow-lg shadow-brand-600/30 group cursor-pointer hover:scale-105 transition-transform">
                    <Volume2 size={16} className="group-hover:animate-pulse" />
                 </div>
                 <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-7" />
            </div>
          </div>
        )}
        
        <div className="p-5 border-b border-navy-50/50 bg-gradient-to-br from-brand-50/30 via-white to-transparent">
          <div className="flex flex-col md:flex-row items-start justify-between gap-3 mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-brand-600 rounded-lg text-white shadow-xl shadow-brand-600/20 rotate-2 hover:rotate-0 transition-transform duration-300">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-black text-navy-900 tracking-tight leading-none mb-1">Health Assessment</h3>
                {report?.patient_name && (
                  <div className="text-[10px] font-bold text-brand-600 uppercase tracking-widest mb-1">
                    Name: {report.patient_name}
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <SeverityBadge level={report.severity || "MODERATE"} />
                  <span className="w-1 h-1 rounded-full bg-navy-200" />
                  <span className="text-[8px] font-bold text-navy-400 uppercase tracking-widest">AI Analysis</span>
                </div>
              </div>
            </div>
            <button 
              onClick={handleDownload}
              disabled={downloading}
              className="group flex items-center gap-2 px-4 py-2 rounded-xl bg-navy-900 text-[11px] font-bold text-white hover:bg-brand-600 transition-all shadow-lg shadow-navy-900/10 active:scale-95 disabled:opacity-50"
            >
              {downloading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Download className="h-3.5 w-3.5 group-hover:-translate-y-0.5 transition-transform" />
              )}
              {downloading ? 'Preparing...' : 'Download Results'}
            </button>
          </div>
          
          <div className="space-y-3">
            <div className="relative">
              <div className="absolute -left-3 top-0 bottom-0 w-0.5 bg-brand-500 rounded-full opacity-50" />
              <p className="text-navy-800 text-sm leading-relaxed font-semibold italic">"{report.health_information || report.summary}"</p>
            </div>
            {report.ai_confidence && <ConfidenceBar score={report.ai_confidence} />}
          </div>
        </div>

        <div className="p-5 space-y-5">
          {report.possible_conditions?.length > 0 && (
            <div className="animate-fade-in-up">
              <h4 className="text-[9px] font-black text-navy-400 uppercase tracking-[0.15em] mb-3 flex items-center gap-2">
                <div className="h-px w-4 bg-navy-100" />
                Considerations
              </h4>
              <div className="flex flex-wrap gap-2">
                {report.possible_conditions.map((cond, i) => (
                  <span key={i} className="px-3 py-1.5 bg-white text-navy-800 text-[10px] font-bold rounded-lg border border-navy-100 shadow-sm hover:border-brand-300 hover:shadow-md transition-all cursor-default">
                    {cond}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-brand-50/50 rounded-xl p-4 border border-brand-100/50 relative overflow-hidden group hover:shadow-lg transition-all duration-300">
              <div className="absolute -top-3 -right-3 p-4 opacity-5 group-hover:opacity-10 transition-opacity rotate-12 group-hover:rotate-0 duration-500">
                <Stethoscope size={80} />
              </div>
              <h4 className="text-brand-900 font-black text-[10px] mb-2.5 flex items-center gap-2 relative z-10">
                <div className="p-1 bg-brand-100 rounded-md">
                    <Stethoscope className="h-3 w-3" />
                </div>
                Clinical Steps
              </h4>
              <p className="text-brand-800 text-[11px] leading-relaxed font-bold relative z-10">{report.recommended_next_steps}</p>
            </div>
            
            {report.trusted_sources?.length > 0 && (
              <div className="bg-emerald-50/50 rounded-xl p-4 border border-emerald-100/50 relative overflow-hidden group hover:shadow-lg transition-all duration-300">
                <div className="absolute -top-3 -right-3 p-4 opacity-5 group-hover:opacity-10 transition-opacity -rotate-12 group-hover:rotate-0 duration-500">
                  <ShieldCheck size={80} />
                </div>
                <h4 className="text-emerald-900 font-black text-[10px] mb-2.5 flex items-center gap-2 relative z-10">
                  <div className="p-1 bg-emerald-100 rounded-md">
                    <ShieldCheck className="h-3 w-3" />
                  </div>
                  Sources
                </h4>
                <ul className="text-emerald-800 text-[10px] space-y-2 font-bold relative z-10">
                  {report.trusted_sources.map((src, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <div className="w-1 h-1 bg-emerald-400 rounded-full shadow-sm" />
                      {src}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <FeedbackSection 
          feedbackGiven={feedbackGiven} 
          onFeedback={handleFeedback} 
          onNegativeClick={() => setIsModalOpen(true)}
        />

        <FeedbackModal 
          isOpen={isModalOpen} 
          onClose={() => setIsModalOpen(false)} 
          onSubmit={handleNegativeSubmit} 
        />

        <div className="px-5 py-3 bg-navy-50/30 border-t border-navy-100/40 flex items-start gap-3">
          <div className="p-1 bg-white rounded-md border border-navy-100/50 shadow-sm">
            <Info className="h-3.5 w-3.5 text-navy-400" />
          </div>
          <p className="text-[9px] text-navy-400 leading-relaxed font-bold uppercase tracking-wide">
            Medical Disclaimer: {report.disclaimer || "This analysis is for informational purposes only. Consult a physician for any medical concerns."}
          </p>
        </div>
      </div>
    );
  }

  // Handle Medical Report Analysis (New Strict Format)
  if (report?.type === 'medical_report_analysis') {
    return (
      <div className="bg-white rounded-2xl shadow-premium border border-navy-100/60 overflow-hidden max-w-xl animate-slide-up hover:shadow-xl transition-all duration-500">
        {audioUrl && (
          <div className="px-5 pt-5">
            <div className="bg-navy-50/50 rounded-xl p-2.5 flex items-center gap-3 border border-navy-100/40 backdrop-blur-sm">
                 <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center text-white shadow-lg shadow-brand-600/30">
                    <Volume2 size={16} />
                 </div>
                 <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-7" />
            </div>
          </div>
        )}
        
        <div className="p-5 border-b border-navy-50/50 bg-gradient-to-br from-brand-50/30 via-white to-transparent">
          <div className="flex flex-col md:flex-row items-start justify-between gap-3 mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-brand-600 rounded-lg text-white shadow-xl shadow-brand-600/20 rotate-2">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-black text-navy-900 tracking-tight leading-none mb-1">Lab Analysis</h3>
                {report?.patient_name && (
                  <div className="text-[10px] font-bold text-brand-600 uppercase tracking-widest mb-1">
                    Name: {report.patient_name}
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <SeverityBadge level={report.severity || "LOW"} />
                  <span className="w-1 h-1 rounded-full bg-navy-200" />
                  <span className="text-[8px] font-bold text-navy-400 uppercase tracking-widest">Lab Insights</span>
                </div>
              </div>
            </div>
            <button 
              onClick={handleDownload}
              disabled={downloading}
              className="group flex items-center gap-2 px-4 py-2 rounded-xl bg-navy-900 text-[11px] font-bold text-white hover:bg-brand-600 transition-all shadow-lg shadow-navy-900/10 active:scale-95 disabled:opacity-50"
            >
              {downloading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Download className="h-3.5 w-3.5 group-hover:-translate-y-0.5 transition-transform" />
              )}
              {downloading ? 'Preparing...' : 'Download'}
            </button>
          </div>
          
          <div className="space-y-3">
            <div className="relative">
              <div className="absolute -left-3 top-0 bottom-0 w-0.5 bg-brand-500 rounded-full opacity-50" />
              <p className="text-navy-700 text-sm leading-relaxed font-semibold">{report.summary}</p>
            </div>
            
            {report.health_information && (
              <div className="relative mt-3 pt-3 border-t border-navy-50/50">
                <div className="absolute -left-3 top-3 bottom-0 w-0.5 bg-brand-500 rounded-full opacity-50" />
                <div className="text-navy-800 text-[11px] leading-relaxed font-semibold italic prose prose-sm prose-navy max-w-none">
                  <ReactMarkdown>{report.health_information}</ReactMarkdown>
                </div>
              </div>
            )}
            
            {report.summary?.includes("seek medical attention") && (
              <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-start gap-3 animate-pulse-soft shadow-sm shadow-rose-500/10">
                <div className="p-2 bg-rose-100 rounded-lg text-rose-600">
                  <AlertOctagon className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="text-rose-900 font-black text-[10px] uppercase tracking-wider mb-1">Critical Alert</h4>
                  <p className="text-rose-700 text-[11px] font-bold leading-relaxed">
                    Some values are significantly outside the normal range. Consult a professional.
                  </p>
                </div>
              </div>
            )}

            {report.ai_confidence && <ConfidenceBar score={report.ai_confidence} />}
          </div>
        </div>

        <div className="p-5">
          <h4 className="text-[9px] font-black text-navy-400 uppercase tracking-[0.15em] mb-3 flex items-center gap-2">
            <div className="h-px w-4 bg-navy-100" />
            Test Breakdown
          </h4>
          <div className="overflow-hidden rounded-xl border border-navy-100 shadow-sm bg-white">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-navy-50/50">
                  <tr>
                    <th className="px-4 py-3 font-black text-navy-900 uppercase tracking-widest text-[8px]">Test</th>
                    <th className="px-4 py-3 font-black text-navy-900 uppercase tracking-widest text-[8px]">Result</th>
                    <th className="px-4 py-3 font-black text-navy-900 uppercase tracking-widest text-[8px]">Ref.</th>
                    <th className="px-4 py-3 font-black text-navy-900 uppercase tracking-widest text-[8px]">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-50">
                  {report.test_analysis?.map((test, i) => (
                    <tr key={i} className="hover:bg-brand-50/30 transition-colors group">
                      <td className="px-4 py-3">
                        <div className="font-bold text-navy-900 text-xs">{test.test_name}</div>
                        <div className="text-[9px] text-navy-400 font-bold mt-0.5 leading-relaxed flex items-start gap-1.5">
                          <Info size={9} className="mt-0.5 shrink-0" />
                          {test.explanation}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-navy-900 font-black text-xs tabular-nums">{test.value}</td>
                      <td className="px-4 py-3 text-navy-500 font-bold text-[10px]">{test.normal_range}</td>
                      <td className="px-4 py-3">
                        <span className={clsx(
                          "px-2 py-0.5 rounded-md text-[8px] font-black uppercase tracking-widest shadow-sm border",
                          test.status?.toLowerCase() === 'normal' ? "bg-emerald-50 text-emerald-700 border-emerald-100" : 
                          test.status?.toLowerCase() === 'borderline' ? "bg-amber-50 text-amber-700 border-amber-100" :
                          (test.status?.toLowerCase() === 'high' || test.status?.toLowerCase() === 'low') ? "bg-rose-50 text-rose-700 border-rose-100" :
                          "bg-navy-50 text-navy-700 border-navy-100"
                        )}>
                          {test.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-emerald-50/50 rounded-xl p-4 border border-emerald-100/50 group hover:shadow-lg transition-all">
              <h4 className="text-emerald-900 font-black text-[10px] mb-3 flex items-center gap-2">
                <div className="p-1 bg-emerald-100 rounded-md">
                  <Utensils className="h-3 w-3" />
                </div>
                Lifestyle
              </h4>
              <ul className="text-emerald-800 text-[10px] space-y-2 font-bold">
                {report.general_guidance?.map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <div className="w-1 h-1 bg-emerald-400 rounded-full mt-1 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-amber-50/50 rounded-xl p-4 border border-amber-100/50 group hover:shadow-lg transition-all">
              <h4 className="text-amber-900 font-black text-[10px] mb-3 flex items-center gap-2">
                <div className="p-1 bg-amber-100 rounded-md">
                  <Stethoscope className="h-3 w-3" />
                </div>
                Consultation
              </h4>
              <ul className="text-amber-800 text-[10px] space-y-2 font-bold">
                {report.when_to_consult_doctor?.map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <div className="w-1 h-1 bg-amber-400 rounded-full mt-1 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <FeedbackSection 
          feedbackGiven={feedbackGiven} 
          onFeedback={handleFeedback} 
          onNegativeClick={() => setIsModalOpen(true)}
        />

        <FeedbackModal 
          isOpen={isModalOpen} 
          onClose={() => setIsModalOpen(false)} 
          onSubmit={handleNegativeSubmit} 
        />

        <div className="px-5 py-3 bg-navy-50/30 border-t border-navy-100/40 flex items-start gap-3">
          <div className="p-1 bg-white rounded-md border border-navy-100/50 shadow-sm">
            <Info className="h-3.5 w-3.5 text-navy-400" />
          </div>
          <p className="text-[9px] text-navy-400 leading-relaxed font-bold uppercase tracking-wide">
            Medical Disclaimer: {report.disclaimer || "Laboratory results must be interpreted by a physician in the context of your overall clinical history."}
          </p>
        </div>
      </div>
    );
  }

  // Handle Medical Report Analysis (Legacy Format)
  if (report?.input_type === 'medical_report') {
    return (
      <div className="bg-white rounded-2xl shadow-premium border border-navy-100 overflow-hidden max-w-xl animate-slide-up hover:shadow-xl transition-all duration-500">
        {audioUrl && (
          <div className="px-5 pt-5">
            <div className="bg-navy-50 rounded-xl p-2.5 flex items-center gap-3 border border-navy-100/50">
                 <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
                    <Volume2 size={16} />
                 </div>
                 <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-7 bg-transparent" />
            </div>
          </div>
        )}
        
        <div className="p-5 border-b border-navy-50 bg-gradient-to-br from-teal-50/50 via-white to-transparent">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-teal-600 rounded-xl text-white shadow-lg shadow-teal-600/20">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-black text-navy-900 tracking-tight leading-none">{report.report_type || "Lab Analysis"}</h3>
                {report?.patient_name && (
                  <div className="text-[10px] font-bold text-teal-600 uppercase tracking-widest mt-1">
                    Name: {report.patient_name}
                  </div>
                )}
                <div className="flex items-center gap-2 mt-1">
                    <span className="px-2 py-0.5 bg-teal-50 text-teal-700 text-[8px] font-bold uppercase rounded-md border border-teal-100">Legacy</span>
                </div>
              </div>
            </div>
            <button 
              onClick={handleDownload}
              disabled={downloading}
              className="group flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-navy-100 text-[11px] font-bold text-navy-600 hover:text-brand-600 hover:border-brand-200 hover:bg-brand-50 transition-all shadow-sm active:scale-95"
            >
              {downloading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-brand-600" />
              ) : (
                <Download className="h-3.5 w-3.5 group-hover:-translate-y-0.5 transition-transform" />
              )}
              {downloading ? 'Preparing...' : 'Export PDF'}
            </button>
          </div>
          <p className="text-navy-700 text-sm leading-relaxed font-medium">{report.interpretation}</p>
        </div>

        <div className="p-5">
          <h4 className="text-[9px] font-bold text-navy-400 uppercase tracking-widest mb-4 flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-brand-500" />
            Markers
          </h4>
          <div className="overflow-hidden rounded-xl border border-navy-100 shadow-sm">
            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-navy-50/50">
                <tr>
                  <th className="px-4 py-3 font-bold text-navy-900 uppercase tracking-wider text-[8px]">Marker</th>
                  <th className="px-4 py-3 font-bold text-navy-900 uppercase tracking-wider text-[8px]">Value</th>
                  <th className="px-4 py-3 font-bold text-navy-900 uppercase tracking-wider text-[8px]">Ref.</th>
                  <th className="px-4 py-3 font-bold text-navy-900 uppercase tracking-wider text-[8px]">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-50">
                {report.key_values?.map((kv, i) => (
                  <tr key={i} className="hover:bg-brand-50/30 transition-colors">
                    <td className="px-4 py-3 font-bold text-navy-900 text-xs">{kv.marker}</td>
                    <td className="px-4 py-3 text-navy-900 font-bold text-xs">{kv.value}</td>
                    <td className="px-4 py-3 text-navy-500 font-medium text-[10px]">{kv.range}</td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        "px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-wider",
                        kv.status?.toLowerCase() === 'normal' ? "bg-teal-50 text-teal-700" : "bg-red-50 text-red-700"
                      )}>
                        {kv.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-5 bg-brand-50 rounded-xl p-4 border border-brand-100 group">
            <h4 className="text-brand-900 font-bold text-[10px] mb-2 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4" />
              Recommendation
            </h4>
            <p className="text-brand-800 text-[11px] leading-relaxed font-medium">{report.recommendation}</p>
          </div>
        </div>

        <FeedbackSection 
          feedbackGiven={feedbackGiven} 
          onFeedback={handleFeedback} 
          onNegativeClick={() => setIsModalOpen(true)}
        />

        <FeedbackModal 
          isOpen={isModalOpen} 
          onClose={() => setIsModalOpen(false)} 
          onSubmit={handleNegativeSubmit} 
        />

        <div className="px-5 py-3 bg-navy-50/50 border-t border-navy-100 flex items-start gap-3">
          <Info className="h-3.5 w-3.5 text-navy-300 mt-0.5 shrink-0" />
          <p className="text-[9px] text-navy-400 leading-relaxed font-medium">{report.disclaimer}</p>
        </div>
      </div>
    );
  }

  // Handle Clarification Questions (Triage Mode)
  if (report?.type === 'clarification_questions') {
    const isLatest = report.isLatest !== false;

    return (
      <div className="bg-gradient-to-br from-brand-600 to-navy-900 rounded-2xl p-5 shadow-premium border border-white/10 animate-slide-up relative overflow-hidden group max-w-xl">
         {/* Decorative elements - Scaled */}
         <div className="absolute -top-20 -right-20 w-40 h-40 bg-white/5 rounded-full blur-3xl group-hover:bg-white/10 transition-colors" />
         <div className="absolute -bottom-20 -left-20 w-40 h-40 bg-brand-400/5 rounded-full blur-3xl group-hover:bg-brand-400/10 transition-colors" />

         {audioUrl && (
            <div className="mb-5 bg-white/10 backdrop-blur-md p-2.5 rounded-xl flex items-center gap-4 border border-white/20 shadow-xl">
                <div className="w-9 h-9 bg-white rounded-lg flex items-center justify-center text-brand-600 shadow-lg group-hover:scale-105 transition-transform">
                    <Volume2 size={16} className="animate-pulse" />
                </div>
                <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-7 invert brightness-200" />
            </div>
         )}
         
         <div className="flex items-center gap-4 mb-5 relative z-10">
            <div className="p-2.5 bg-white/15 backdrop-blur-sm rounded-xl shadow-inner border border-white/20 rotate-3 group-hover:rotate-0 transition-transform">
                <HelpCircle className="h-5 w-5 text-white" />
            </div>
            <div>
                <h3 className="text-lg font-black text-white tracking-tight leading-none mb-1.5">Clarification Needed</h3>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 bg-white/20 text-white text-[7px] font-black uppercase rounded-md border border-white/10 backdrop-blur-sm tracking-widest">Triage Mode</span>
                  <span className="w-1 h-1 rounded-full bg-white/30" />
                  <span className="text-[7px] font-bold text-white/60 uppercase tracking-widest">{isLatest ? 'Pending' : 'Answered'}</span>
                </div>
            </div>
         </div>

         <p className="text-white/90 mb-5 leading-relaxed font-bold text-sm relative z-10 italic">"{report.context}"</p>
         
         <div className="space-y-2.5 relative z-10">
            {report.questions && report.questions.map((q, i) => (
                <div key={i} className="bg-white/5 backdrop-blur-md p-3 rounded-xl border border-white/10 text-white font-bold shadow-lg flex gap-3 hover:bg-white/10 hover:border-white/30 transition-all group/item cursor-pointer">
                    <span className="flex-shrink-0 w-7 h-7 bg-white/10 text-white rounded-lg flex items-center justify-center text-[10px] font-black border border-white/10 group-hover/item:bg-white group-hover/item:text-brand-600 transition-all">{i + 1}</span>
                    <span className="mt-1 text-xs group-hover/item:translate-x-1 transition-transform">{q}</span>
                </div>
            ))}
         </div>
         
         {isLatest && (
            <div className="mt-5 flex items-center gap-3 px-1 relative z-10">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                  <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                  <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" />
                </div>
                <p className="text-[8px] text-white/50 font-black uppercase tracking-widest">Awaiting response</p>
            </div>
         )}
      </div>
    );
  }

  // Handle Medical Image Analysis (Strict Format)
  if (report?.input_type === 'medical_image') {
    if (report.status === 'HITL_ESCALATED') {
      return (
        <div className="bg-white rounded-2xl shadow-premium border border-navy-100/60 overflow-hidden max-w-xl animate-slide-up hover:shadow-xl transition-all duration-500">
          <div className="p-5 bg-gradient-to-br from-orange-50/50 via-white to-transparent border-b border-navy-50/50">
            <div className="flex items-center gap-4 mb-5">
              <div className="p-3 bg-orange-600 rounded-xl text-white shadow-lg shadow-orange-600/20 rotate-3 hover:rotate-0 transition-transform duration-300">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-black text-navy-900 tracking-tight leading-none mb-1.5">Review Required</h3>
                {report?.patient_name && (
                  <div className="text-[10px] font-bold text-orange-600 uppercase tracking-widest mb-1">
                    Name: {report.patient_name}
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-orange-50 text-orange-700 text-[8px] font-black uppercase rounded-md border border-orange-100 tracking-widest">Safety Escalation</span>
                  <span className="w-1 h-1 rounded-full bg-navy-200" />
                  <span className="text-[8px] font-bold text-navy-400 uppercase tracking-widest italic">Assessment Pending</span>
                </div>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="relative">
                <div className="absolute -left-3 top-0 bottom-0 w-0.5 bg-orange-500 rounded-full opacity-50" />
                <p className="text-navy-800 text-sm leading-relaxed font-semibold italic">"{report.message}"</p>
              </div>
              
              <div className="bg-navy-50/50 p-4 rounded-xl border border-navy-100/50 flex items-start gap-3">
                <Brain className="h-4 w-4 text-navy-400 mt-0.5 shrink-0" />
                <div>
                  <h4 className="text-[9px] font-black text-navy-400 uppercase tracking-widest mb-1">Escalation Reason</h4>
                  <p className="text-navy-700 text-xs font-bold leading-relaxed">{report.reason}</p>
                </div>
              </div>
            </div>
          </div>

          <FeedbackSection 
          feedbackGiven={feedbackGiven} 
          onFeedback={handleFeedback} 
          onNegativeClick={() => setIsModalOpen(true)}
        />

        <FeedbackModal 
          isOpen={isModalOpen} 
          onClose={() => setIsModalOpen(false)} 
          onSubmit={handleNegativeSubmit} 
        />

          <div className="px-5 py-4 bg-orange-50/30 border-t border-orange-100/40 flex items-start gap-4">
            <div className="p-1.5 bg-white rounded-lg border border-orange-100/50 shadow-sm">
              <Info className="h-4 w-4 text-orange-400" />
            </div>
            <p className="text-[10px] text-orange-800/70 leading-relaxed font-bold uppercase tracking-wide">
              Medical Disclaimer: {report.disclaimer || "Our clinical team is reviewing your case. Please wait for an updated assessment."}
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="bg-white rounded-2xl shadow-premium border border-navy-100/60 overflow-hidden max-w-xl animate-slide-up hover:shadow-xl transition-all duration-500">
        {audioUrl && (
          <div className="px-5 pt-5">
            <div className="bg-navy-50/50 rounded-xl p-3 flex items-center gap-4 border border-navy-100/40 backdrop-blur-sm">
                 <div className="w-10 h-10 bg-teal-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-teal-600/30 group cursor-pointer hover:scale-105 transition-transform">
                    <Volume2 size={18} className="group-hover:animate-pulse" />
                 </div>
                 <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-8" />
            </div>
          </div>
        )}

        <div className="p-5 border-b border-navy-50/50 bg-gradient-to-br from-teal-50/30 via-white to-transparent">
          <div className="flex flex-col md:flex-row items-start justify-between gap-4 mb-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-teal-600 rounded-xl text-white shadow-lg shadow-teal-600/20 rotate-3 hover:rotate-0 transition-transform duration-300">
                <ImageIcon className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-black text-navy-900 tracking-tight leading-none mb-1.5">Visual Assessment</h3>
                {report?.patient_name && (
                  <div className="text-[10px] font-bold text-teal-600 uppercase tracking-widest mb-1.5">
                    Name: {report.patient_name}
                  </div>
                )}
                <div className="flex items-center gap-2.5">
                  <SeverityBadge level={report.severity || "MODERATE"} />
                  <span className="w-1 h-1 rounded-full bg-navy-200" />
                  <span className="text-[9px] font-bold text-navy-400 uppercase tracking-widest">AI Analysis</span>
                </div>
              </div>
            </div>
            <button 
              onClick={handleDownload}
              disabled={downloading}
              className="group flex items-center gap-2 px-4 py-2 rounded-xl bg-navy-900 text-[11px] font-bold text-white hover:bg-teal-600 transition-all shadow-lg shadow-navy-900/10 active:scale-95 disabled:opacity-50"
            >
              {downloading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Download className="h-3.5 w-3.5 group-hover:-translate-y-0.5 transition-transform" />
              )}
              {downloading ? 'Preparing...' : 'Download Results'}
            </button>
          </div>
          
          <div className="flex flex-wrap gap-2 mb-4">
            {report.observations?.map((obs, i) => (
              <span key={i} className="px-3 py-1.5 bg-white text-teal-800 text-[10px] font-bold rounded-lg border border-teal-100 shadow-sm hover:border-teal-300 hover:shadow-md transition-all cursor-default flex items-center gap-2">
                <div className="w-1 h-1 rounded-full bg-teal-400" />
                {obs}
              </span>
            ))}
          </div>

          <div className="space-y-3">
            <div className="relative">
              <div className="absolute -left-3 top-0 bottom-0 w-0.5 bg-teal-500 rounded-full opacity-50" />
              <p className="text-navy-800 text-[11px] leading-relaxed font-semibold italic">"{report.health_information || report.summary}"</p>
            </div>
            {report.confidence_level && (
              <div className="flex items-center gap-2">
                <span className="text-[8px] font-bold text-navy-400 uppercase tracking-widest">AI Confidence</span>
                <span className={clsx(
                  "px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-widest border",
                  report.confidence_level.toLowerCase().includes('high') ? "bg-emerald-50 text-emerald-700 border-emerald-100" :
                  report.confidence_level.toLowerCase().includes('medium') ? "bg-amber-50 text-amber-700 border-amber-100" :
                  "bg-orange-50 text-orange-700 border-orange-100"
                )}>
                  {report.confidence_level}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="p-5 space-y-6">
          {report.possible_conditions?.length > 0 && (
            <div className="animate-fade-in-up">
              <h4 className="text-[9px] font-black text-navy-400 uppercase tracking-[0.15em] mb-3 flex items-center gap-2">
                <div className="h-px w-4 bg-navy-100" />
                Clinical Considerations
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {report.possible_conditions.map((cond, i) => (
                  <div key={i} className="bg-navy-50/50 p-3 rounded-xl border border-navy-100/50 flex items-start gap-3 group hover:bg-white hover:shadow-md transition-all">
                    <div className="p-1.5 bg-white rounded-lg shadow-sm border border-navy-100 group-hover:border-teal-200">
                      <Brain className="h-3.5 w-3.5 text-teal-600" />
                    </div>
                    <span className="text-navy-800 text-[11px] font-bold leading-snug pt-0.5">{cond}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="bg-orange-50/50 rounded-2xl p-5 border border-orange-100/50 relative overflow-hidden group hover:shadow-lg transition-all duration-300">
            <div className="absolute -top-3 -right-3 p-6 opacity-5 group-hover:opacity-10 transition-opacity rotate-12 group-hover:rotate-0 duration-500">
              <Utensils size={80} />
            </div>
            <h4 className="text-orange-900 font-black text-[10px] mb-3 flex items-center gap-2 relative z-10">
              <div className="p-1.5 bg-orange-100 rounded-lg">
                <Utensils className="h-3.5 w-3.5" />
              </div>
              Care Advice
            </h4>
            <p className="text-orange-800 text-xs leading-relaxed font-bold relative z-10">{report.general_advice}</p>
          </div>
        </div>

        <FeedbackSection 
          feedbackGiven={feedbackGiven} 
          onFeedback={handleFeedback} 
          onNegativeClick={() => setIsModalOpen(true)}
        />

        <FeedbackModal 
          isOpen={isModalOpen} 
          onClose={() => setIsModalOpen(false)} 
          onSubmit={handleNegativeSubmit} 
        />

        <div className="px-5 py-4 bg-navy-50/30 border-t border-navy-100/40 flex items-start gap-4">
          <div className="p-1.5 bg-white rounded-lg border border-navy-100/50 shadow-sm">
            <Info className="h-4 w-4 text-navy-400" />
          </div>
          <p className="text-[10px] text-navy-400 leading-relaxed font-bold uppercase tracking-wide">
            Medical Disclaimer: {report.disclaimer || "This visual analysis is for informational purposes only. Image quality may affect results."}
          </p>
        </div>
      </div>
    );
  }

  // Handle Legacy or Error Formats
  const mainContent = report?.summary || report?.health_information || report?.interpretation || report?.message || report?.context || report?.analysis || report?.reasoning_brief;
  
  if (!report || !mainContent) {
    return (
      <div className="bg-white rounded-[2rem] p-8 shadow-premium border border-navy-100/60 animate-fade-in flex flex-col md:flex-row items-start md:items-center gap-6 prose prose-navy max-w-none">
        <div className="p-4 bg-navy-50 rounded-2xl text-navy-400 shrink-0">
          <Info className="h-6 w-6" />
        </div>
        <div className="flex-1">
          <ReactMarkdown>
            {typeof report === 'string' ? report : "Report data is being processed or contains no summary."}
          </ReactMarkdown>
        </div>
        <div className="ml-auto shrink-0 pt-4 md:pt-0">
          <FeedbackSection 
            feedbackGiven={feedbackGiven} 
            onFeedback={handleFeedback} 
            onNegativeClick={() => setIsModalOpen(true)}
          />
        </div>

        <FeedbackModal 
          isOpen={isModalOpen} 
          onClose={() => setIsModalOpen(false)} 
          onSubmit={handleNegativeSubmit} 
        />
      </div>
    );
  }

  // Normalize Data Structure (Backwards Compatibility)
  const reportSummary = mainContent;
  const severity = report.risk_assessment?.severity || report.severity || "UNKNOWN";
  const confidence = report.risk_assessment?.confidence_score || 0.0;
  const uncertainty = report.risk_assessment?.uncertainty_reason;
  const explanation = report.explanation || {};
  const recommendations = report.recommendations || {};
  const food_advice = recommendations.food_advice || report.food_recommendations || [];
  const lifestyle_advice = recommendations.lifestyle_advice || report.recommended_actions || [];
  const immediate_action = recommendations.immediate_action;
  const specialist = report.recommended_specialist;

  return (
    <div className="bg-white rounded-2xl shadow-premium border border-navy-100/60 overflow-hidden max-w-xl animate-slide-up hover:shadow-xl transition-all duration-500">
      {audioUrl && (
          <div className="px-5 pt-5">
            <div className="bg-navy-50/50 rounded-xl p-3 flex items-center gap-4 border border-navy-100/40 backdrop-blur-sm">
                 <div className="w-10 h-10 bg-brand-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-brand-600/30 group cursor-pointer hover:scale-105 transition-transform">
                    <Volume2 size={18} className="group-hover:animate-pulse" />
                 </div>
                 <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-8" />
            </div>
          </div>
        )}
      
      {/* Header */}
      <div className="p-5 border-b border-navy-50/50 bg-gradient-to-br from-brand-50/30 via-white to-transparent">
        <div className="flex flex-col md:flex-row items-start justify-between gap-4 mb-5">
          <div className="flex items-center gap-4">
            <div className="p-2.5 bg-brand-600 rounded-xl text-white shadow-xl shadow-brand-600/20 rotate-3 hover:rotate-0 transition-transform duration-300">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-lg font-black text-navy-900 tracking-tight leading-none mb-1.5">Health Assessment</h3>
              <div className="flex items-center gap-2">
                <SeverityBadge level={severity} />
                <span className="w-1 h-1 rounded-full bg-navy-200" />
                <span className="text-[8px] font-bold text-navy-400 uppercase tracking-widest">Clinical Insight</span>
              </div>
            </div>
          </div>
          <button 
            onClick={handleDownload}
            disabled={downloading}
            className="group flex items-center gap-2 px-4 py-2 rounded-xl bg-navy-900 text-[11px] font-bold text-white hover:bg-brand-600 transition-all shadow-lg shadow-navy-900/10 active:scale-95 disabled:opacity-50"
          >
            {downloading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5 group-hover:-translate-y-0.5 transition-transform" />
            )}
            {downloading ? 'Preparing...' : 'Download'}
          </button>
        </div>

        <div className="space-y-3">
          <div className="relative">
            <div className="absolute -left-3 top-0 bottom-0 w-0.5 bg-brand-500 rounded-full opacity-50" />
            <p className="text-navy-800 text-xs leading-relaxed font-semibold italic">"{reportSummary}"</p>
          </div>
          
          {report.health_information && reportSummary !== report.health_information && (
            <div className="relative mt-3 pt-3 border-t border-navy-50/50">
              <div className="absolute -left-3 top-3 bottom-0 w-0.5 bg-brand-500 rounded-full opacity-50" />
              <div className="text-navy-800 text-[11px] leading-relaxed font-semibold italic prose prose-sm prose-navy max-w-none">
                <ReactMarkdown>{report.health_information}</ReactMarkdown>
              </div>
            </div>
          )}
          
          {confidence > 0 && <ConfidenceBar score={confidence} reason={uncertainty} />}
        </div>
      </div>

      {/* Recommendations Grid */}
      <div className="p-5 space-y-5">
        
        {/* Specialist Suggestion */}
        {specialist && (
            <div className="bg-teal-50/50 rounded-xl p-3 border border-teal-100/50 relative overflow-hidden group hover:shadow-lg transition-all duration-300">
                <div className="absolute -top-3 -right-3 p-4 opacity-5 group-hover:opacity-10 transition-opacity rotate-12 group-hover:rotate-0 duration-500">
                  <UserIcon size={60} />
                </div>
                <div className="flex items-start gap-3 relative z-10">
                    <div className="p-2 bg-teal-100 rounded-lg text-teal-600 shadow-sm border border-teal-200/50">
                        <UserIcon className="w-3.5 h-3.5" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-teal-900 font-black text-[8px] uppercase tracking-wider">Specialist</h4>
                          <span className="px-1.5 py-0.5 bg-white text-teal-600 text-[7px] font-black uppercase rounded border border-teal-200 tracking-widest shadow-sm">
                              {specialist.urgency}
                          </span>
                        </div>
                        <p className="text-teal-900 text-xs font-bold mb-0.5">{specialist.type}</p>
                        <p className="text-teal-700 text-[10px] font-medium leading-relaxed">{specialist.reason}</p>
                    </div>
                </div>
            </div>
        )}

        {/* Explainability Panel */}
        {explanation.reasoning && (
          <div className="bg-navy-50/50 rounded-xl border border-navy-100/50 overflow-hidden group">
            <button 
              onClick={() => setShowExplanation(!showExplanation)}
              className="w-full flex items-center justify-between p-3 text-left hover:bg-white transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-1.5 bg-white rounded-lg shadow-sm border border-navy-100 group-hover:border-brand-200">
                  <Brain className="h-3.5 w-3.5 text-brand-500" />
                </div>
                <div>
                  <h4 className="text-navy-900 font-black text-[8px] uppercase tracking-wider">Reasoning</h4>
                  <p className="text-navy-400 text-[7px] font-bold uppercase tracking-widest mt-0.5">AI Methodology</p>
                </div>
              </div>
              <div className={clsx(
                "w-5 h-5 rounded-full flex items-center justify-center transition-all border border-navy-100 shadow-sm",
                showExplanation ? "bg-brand-600 text-white border-brand-600 rotate-180" : "bg-white text-navy-400 hover:text-brand-600"
              )}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>
              </div>
            </button>
            
            {showExplanation && (
              <div className="px-3 pb-3 animate-fade-in">
                <div className="h-px w-full bg-navy-100/50 mb-3" />
                <div className="space-y-2.5">
                  <div className="flex gap-2">
                    <div className="w-1 h-1 rounded-full bg-brand-400 mt-1.5 shrink-0" />
                    <p className="text-navy-700 text-[10px] leading-relaxed font-bold italic">"{explanation.reasoning}"</p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {explanation.history_factor && (
                       <div className="p-2 bg-white rounded-lg border border-navy-100 shadow-sm">
                         <h5 className="text-[7px] font-black text-navy-400 uppercase tracking-widest mb-0.5">History Factor</h5>
                         <p className="text-navy-800 text-[9px] font-bold leading-relaxed">{explanation.history_factor}</p>
                       </div>
                    )}
                    {explanation.profile_factor && (
                       <div className="p-2 bg-white rounded-lg border border-navy-100 shadow-sm">
                         <h5 className="text-[7px] font-black text-navy-400 uppercase tracking-widest mb-0.5">Profile Factor</h5>
                         <p className="text-navy-800 text-[9px] font-bold leading-relaxed">{explanation.profile_factor}</p>
                       </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Immediate Action */}
          {immediate_action && (
            <div className="col-span-1 md:col-span-2 bg-brand-50/50 rounded-2xl p-4 border border-brand-100/50 flex items-start gap-4 group hover:shadow-lg transition-all">
               <div className="p-2.5 bg-brand-100 rounded-xl text-brand-600 shadow-sm border border-brand-200/50">
                  <ShieldCheck className="h-4 w-4" />
               </div>
               <div>
                  <h4 className="text-brand-900 font-black text-[9px] uppercase tracking-wider mb-1">Priority Action</h4>
                  <p className="text-brand-800 text-sm font-bold leading-relaxed">{immediate_action}</p>
               </div>
            </div>
          )}

          {/* Possible Conditions */}
          {report.possible_causes && report.possible_causes.length > 0 && (
            <div className="col-span-1 md:col-span-2">
              <h4 className="text-[9px] font-black text-navy-400 uppercase tracking-[0.15em] mb-3 flex items-center gap-2">
                <div className="h-px w-4 bg-navy-100" />
                Diagnostic Considerations
              </h4>
              <div className="flex flex-wrap gap-2">
                {report.possible_causes.map((condition, idx) => (
                  <span key={idx} className="px-3 py-1.5 bg-white text-navy-800 text-[10px] font-bold rounded-lg border border-navy-100 shadow-sm hover:border-brand-300 hover:shadow-md transition-all cursor-default">
                    {condition}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Lifestyle Recommendations */}
          {lifestyle_advice.length > 0 && (
            <div className="bg-emerald-50/50 rounded-2xl p-4 border border-emerald-100/50 group hover:shadow-lg transition-all duration-300 relative overflow-hidden">
              <div className="absolute -top-3 -right-3 p-4 opacity-5 group-hover:opacity-10 transition-opacity rotate-12 group-hover:rotate-0 duration-500">
                <CheckCircle2 size={80} />
              </div>
              <h4 className="text-emerald-900 font-black text-[9px] mb-3 flex items-center gap-2 relative z-10">
                <div className="p-1.5 bg-emerald-100 rounded-lg">
                  <CheckCircle2 className="h-3 w-3" />
                </div>
                Lifestyle Advice
              </h4>
              <ul className="space-y-2 relative z-10">
                {lifestyle_advice.map((action, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-[10px] text-emerald-800 font-bold">
                    <div className="w-1 h-1 rounded-full bg-emerald-400 mt-1.5 shrink-0 shadow-sm" />
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Food Recommendations */}
          {food_advice.length > 0 && (
            <div className="bg-orange-50/50 rounded-2xl p-4 border border-orange-100/50 group hover:shadow-lg transition-all duration-300 relative overflow-hidden">
              <div className="absolute -top-3 -right-3 p-4 opacity-5 group-hover:opacity-10 transition-opacity -rotate-12 group-hover:rotate-0 duration-500">
                <Utensils size={80} />
              </div>
              <h4 className="text-orange-900 font-black text-[9px] mb-3 flex items-center gap-2 relative z-10">
                <div className="p-1.5 bg-orange-100 rounded-lg">
                  <Utensils className="h-3 w-3" />
                </div>
                Nutrition Guide
              </h4>
              <ul className="space-y-2 relative z-10">
                {food_advice.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-[10px] text-orange-800 font-bold">
                    <div className="w-1 h-1 rounded-full bg-orange-400 mt-1.5 shrink-0 shadow-sm" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Trusted Sources */}
          {report.knowledge_sources && report.knowledge_sources.length > 0 && (
            <div className="col-span-1 md:col-span-2">
               <h4 className="text-[10px] font-black text-navy-400 uppercase tracking-[0.2em] mb-4 flex items-center gap-2.5">
                <div className="h-px w-6 bg-navy-100" />
                Verified Clinical Sources
              </h4>
              <div className="grid gap-3 md:grid-cols-2">
                  {report.knowledge_sources.map((src, idx) => (
                      <div key={idx} className="bg-navy-50/50 rounded-xl p-4 border border-navy-100/50 hover:bg-white hover:shadow-md transition-all group">
                          <div className="flex items-center gap-2.5 mb-1.5">
                            <div className="p-1 bg-white rounded-lg border border-navy-100 group-hover:border-brand-200">
                              <FileText className="h-3 w-3 text-brand-600" />
                            </div>
                            <p className="text-[10px] font-black text-navy-900 uppercase tracking-wider">{src.source || "Medical Publication"}</p>
                          </div>
                          <p className="text-navy-600 text-[11px] font-bold leading-relaxed">{src.description}</p>
                      </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <FeedbackSection 
        feedbackGiven={feedbackGiven} 
        onFeedback={handleFeedback} 
        onNegativeClick={() => setIsModalOpen(true)}
      />

      <FeedbackModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        onSubmit={handleNegativeSubmit} 
      />

      {/* Disclaimer Footer */}
      <div className="px-6 py-4 bg-navy-50/30 flex items-start gap-4">
        <div className="p-1.5 bg-white rounded-lg border border-navy-100/50 shadow-sm">
          <Info className="h-4 w-4 text-navy-400" />
        </div>
        <p className="text-[10px] text-navy-400 leading-relaxed font-bold uppercase tracking-wide">
          Medical Disclaimer: {report.disclaimer || "This AI provides preliminary clinical guidance only and is not a substitute for professional medical diagnosis or treatment."}
        </p>
      </div>
    </div>
  );
};

export default ReportCard;
