import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, AlertOctagon, Info, Stethoscope, Utensils, Activity, Download, FileText, Brain, ShieldCheck, ThumbsUp, ThumbsDown, HelpCircle, Volume2, User as UserIcon, Image as ImageIcon } from 'lucide-react';
import clsx from 'clsx';
import { dashboardService, feedbackService } from '../services/api';

const SeverityBadge = ({ level }) => {
  const colors = {
    LOW: "bg-teal-50 text-teal-700 border-teal-200",
    MODERATE: "bg-brand-50 text-brand-700 border-brand-200",
    HIGH: "bg-orange-50 text-orange-700 border-orange-200",
    EMERGENCY: "bg-red-50 text-red-700 border-red-200",
    UNKNOWN: "bg-navy-50 text-navy-700 border-navy-200"
  };

  return (
    <span className={clsx(
      "px-3 py-1 rounded-full text-[10px] font-bold border uppercase tracking-widest",
      colors[level] || colors.UNKNOWN
    )}>
      {level}
    </span>
  );
};

const ConfidenceBar = ({ score, reason }) => {
  // Handle both number (0-1) and string (Low/Medium/High) scores
  let percentage = 0;
  if (typeof score === 'number') {
    percentage = Math.round(score * 100);
  } else if (typeof score === 'string') {
    const s = score.toLowerCase();
    if (s.includes('high')) percentage = 90;
    else if (s.includes('medium')) percentage = 60;
    else if (s.includes('low')) percentage = 30;
  }
  
  const color = percentage > 80 ? "bg-teal-500" : percentage > 50 ? "bg-brand-500" : "bg-orange-500";
  
  return (
    <div className="flex flex-col gap-1.5 w-full max-w-xs">
      <div className="flex justify-between text-[10px] font-bold text-navy-400 uppercase tracking-wider">
        <span>AI Confidence</span>
        <span>{percentage}%</span>
      </div>
      <div className="h-2 w-full bg-navy-50 rounded-full overflow-hidden border border-navy-100/50">
        <div 
          className={clsx("h-full transition-all duration-1000 ease-out rounded-full", color)}
          style={{ width: `${percentage}%` }} 
        />
      </div>
      {reason && <span className="text-[10px] text-navy-300 italic font-medium">{reason}</span>}
    </div>
  );
};

const ReportCard = ({ data, audioUrl }) => {
  const [downloading, setDownloading] = useState(false);
  const [showExplanation, setShowExplanation] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(null);

  const handleFeedback = async (rating) => {
    if (feedbackGiven) return;
    setFeedbackGiven(rating);
    try {
        const context = typeof data === 'string' ? JSON.parse(data).summary : data.summary;
        await feedbackService.submitFeedback(rating, context);
    } catch (e) {
        console.error("Feedback error", e);
    }
  };

  const handleDownload = async () => {
    try {
      setDownloading(true);
      const email = localStorage.getItem('email');
      if (!email) {
        alert("Please log in to download reports.");
        return;
      }
      
      const blob = await dashboardService.getReportPdf(email);
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

  // Safe Parsing
  let report = data;
  if (typeof data === 'string') {
    try {
      report = JSON.parse(data);
    } catch (e) {
      return (
        <div className="bg-white rounded-3xl p-8 shadow-premium border border-navy-100 animate-fade-in">
          <p className="text-navy-900 leading-relaxed font-medium">{data}</p>
        </div>
      );
    }
  }

  // Handle General Health Report (Symptom Analysis)
  if (report?.type === 'health_report') {
    return (
      <div className="bg-white rounded-[2rem] shadow-premium border border-navy-100 overflow-hidden max-w-3xl animate-slide-up">
        {audioUrl && (
          <div className="px-8 pt-6">
            <div className="bg-navy-50 rounded-2xl p-3 flex items-center gap-4 border border-navy-100/50">
                 <div className="w-10 h-10 bg-brand-500 rounded-xl flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
                    <Volume2 size={18} />
                 </div>
                 <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-8 bg-transparent" />
            </div>
          </div>
        )}
        
        <div className="p-8 border-b border-navy-50 bg-gradient-to-br from-brand-50/50 via-white to-transparent">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-brand-600 rounded-2xl text-white shadow-lg shadow-brand-600/20">
                <Activity className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-xl font-extrabold text-navy-900 tracking-tight">Health Assessment</h3>
                <div className="flex items-center gap-2 mt-1">
                  <SeverityBadge level={report.severity || "MODERATE"} />
                </div>
              </div>
            </div>
            <button 
              onClick={handleDownload}
              disabled={downloading}
              className="group flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-white border border-navy-100 text-sm font-bold text-navy-600 hover:text-brand-600 hover:border-brand-200 hover:bg-brand-50 transition-all shadow-sm active:scale-95"
            >
              {downloading ? (
                <Loader2 className="h-4 w-4 animate-spin text-brand-600" />
              ) : (
                <Download className="h-4 w-4 group-hover:-translate-y-0.5 transition-transform" />
              )}
              {downloading ? 'Preparing...' : 'Export PDF'}
            </button>
          </div>
          <p className="text-navy-700 text-base leading-relaxed mb-6 font-medium">{report.health_information || report.summary}</p>
          {report.ai_confidence && <ConfidenceBar score={report.ai_confidence} />}
        </div>

        <div className="p-8 space-y-8">
          {report.possible_conditions?.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-navy-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                <Brain className="h-4 w-4 text-brand-500" />
                Diagnostic Considerations
              </h4>
              <div className="flex flex-wrap gap-2.5">
                {report.possible_conditions.map((cond, i) => (
                  <span key={i} className="px-4 py-2 bg-navy-50 text-navy-700 text-xs font-bold rounded-xl border border-navy-100 shadow-sm hover:bg-white hover:border-brand-200 transition-all">
                    {cond}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-brand-50 rounded-3xl p-6 border border-brand-100 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
                <Stethoscope size={64} />
              </div>
              <h4 className="text-brand-900 font-bold text-sm mb-3 flex items-center gap-2 relative z-10">
                <Stethoscope className="h-4 w-4" />
                Clinical Next Steps
              </h4>
              <p className="text-brand-800 text-sm leading-relaxed font-medium relative z-10">{report.recommended_next_steps}</p>
            </div>
            
            {report.trusted_sources?.length > 0 && (
              <div className="bg-teal-50 rounded-3xl p-6 border border-teal-100 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
                  <ShieldCheck size={64} />
                </div>
                <h4 className="text-teal-900 font-bold text-sm mb-3 flex items-center gap-2 relative z-10">
                  <ShieldCheck className="h-4 w-4" />
                  Verified Sources
                </h4>
                <ul className="text-teal-800 text-xs space-y-2 list-none relative z-10">
                  {report.trusted_sources.map((src, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <div className="w-1 h-1 bg-teal-400 rounded-full" />
                      {src}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <div className="px-8 py-5 bg-navy-50/50 border-t border-navy-100 flex items-start gap-4">
          <Info className="h-5 w-5 text-navy-300 mt-0.5 shrink-0" />
          <p className="text-[11px] text-navy-400 leading-relaxed font-medium">{report.disclaimer}</p>
        </div>
      </div>
    );
  }

  // Handle Medical Report Analysis (New Strict Format)
  if (report?.type === 'medical_report_analysis') {
    return (
      <div className="bg-white rounded-[2rem] shadow-premium border border-navy-100 overflow-hidden max-w-3xl animate-slide-up">
        {audioUrl && (
          <div className="px-8 pt-6">
            <div className="bg-navy-50 rounded-2xl p-3 flex items-center gap-4 border border-navy-100/50">
                 <div className="w-10 h-10 bg-brand-500 rounded-xl flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
                    <Volume2 size={18} />
                 </div>
                 <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-8 bg-transparent" />
            </div>
          </div>
        )}
        
        <div className="p-8 border-b border-navy-50 bg-gradient-to-br from-brand-50/50 via-white to-transparent">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-brand-600 rounded-2xl text-white shadow-lg shadow-brand-600/20">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-xl font-extrabold text-navy-900 tracking-tight">Lab Report Analysis</h3>
                <div className="flex items-center gap-2 mt-1">
                  <SeverityBadge level={report.severity || "LOW"} />
                </div>
              </div>
            </div>
            <button 
              onClick={handleDownload}
              disabled={downloading}
              className="group flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-white border border-navy-100 text-sm font-bold text-navy-600 hover:text-brand-600 hover:border-brand-200 hover:bg-brand-50 transition-all shadow-sm active:scale-95"
            >
              {downloading ? (
                <Loader2 className="h-4 w-4 animate-spin text-brand-600" />
              ) : (
                <Download className="h-4 w-4 group-hover:-translate-y-0.5 transition-transform" />
              )}
              {downloading ? 'Preparing...' : 'Export PDF'}
            </button>
          </div>
          <p className="text-navy-700 text-base leading-relaxed mb-6 font-medium">{report.summary}</p>
          
          {report.summary?.includes("seek medical attention") && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-2xl p-5 flex items-start gap-4 animate-pulse-soft shadow-sm shadow-red-500/10">
              <AlertOctagon className="h-6 w-6 text-red-600 shrink-0 mt-0.5" />
              <p className="text-sm font-bold text-red-700 leading-relaxed">
                Critical Alert: Some values are significantly outside the normal range. Please consult a healthcare professional immediately.
              </p>
            </div>
          )}

          {report.ai_confidence && <ConfidenceBar score={report.ai_confidence} />}
        </div>

        <div className="p-8">
          <h4 className="text-xs font-bold text-navy-400 uppercase tracking-widest mb-6 flex items-center gap-2">
            <Activity className="h-4 w-4 text-brand-500" />
            Comprehensive Test Breakdown
          </h4>
          <div className="overflow-hidden rounded-3xl border border-navy-100 shadow-sm">
            <table className="w-full text-sm text-left border-collapse">
              <thead className="bg-navy-50/50">
                <tr>
                  <th className="px-6 py-4 font-bold text-navy-900 uppercase tracking-wider text-[10px]">Test Name</th>
                  <th className="px-6 py-4 font-bold text-navy-900 uppercase tracking-wider text-[10px]">Value</th>
                  <th className="px-6 py-4 font-bold text-navy-900 uppercase tracking-wider text-[10px]">Normal Range</th>
                  <th className="px-6 py-4 font-bold text-navy-900 uppercase tracking-wider text-[10px]">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-50">
                {report.test_analysis?.map((test, i) => (
                  <tr key={i} className="hover:bg-brand-50/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-bold text-navy-900">{test.test_name}</div>
                      <div className="text-[11px] text-navy-400 font-medium mt-1 leading-relaxed">{test.explanation}</div>
                    </td>
                    <td className="px-6 py-4 text-navy-900 font-bold">{test.value}</td>
                    <td className="px-6 py-4 text-navy-500 font-medium">{test.normal_range}</td>
                    <td className="px-6 py-4">
                      <span className={clsx(
                        "px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider",
                        test.status?.toLowerCase() === 'normal' ? "bg-teal-50 text-teal-700" : 
                        test.status?.toLowerCase() === 'borderline' ? "bg-brand-50 text-brand-700" :
                        (test.status?.toLowerCase() === 'high' || test.status?.toLowerCase() === 'low') ? "bg-red-50 text-red-700" :
                        "bg-navy-50 text-navy-700"
                      )}>
                        {test.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-teal-50 rounded-3xl p-6 border border-teal-100 group">
              <h4 className="text-teal-900 font-bold text-sm mb-4 flex items-center gap-2">
                <Utensils className="h-5 w-5" />
                Dietary & Lifestyle
              </h4>
              <ul className="text-teal-800 text-xs space-y-3 font-medium">
                {report.general_guidance?.map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 bg-teal-400 rounded-full mt-1.5 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-orange-50 rounded-3xl p-6 border border-orange-100 group">
              <h4 className="text-orange-900 font-bold text-sm mb-4 flex items-center gap-2">
                <Stethoscope className="h-5 w-5" />
                Consultation Advice
              </h4>
              <ul className="text-orange-800 text-xs space-y-3 font-medium">
                {report.when_to_consult_doctor?.map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 bg-orange-400 rounded-full mt-1.5 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="px-8 py-5 bg-navy-50/50 border-t border-navy-100 flex items-start gap-4">
          <Info className="h-5 w-5 text-navy-300 mt-0.5 shrink-0" />
          <p className="text-[11px] text-navy-400 leading-relaxed font-medium">{report.disclaimer}</p>
        </div>
      </div>
    );
  }

  // Handle Medical Report Analysis (Legacy Format)
  if (report?.input_type === 'medical_report') {
    return (
      <div className="bg-white rounded-[2rem] shadow-premium border border-navy-100 overflow-hidden max-w-3xl animate-slide-up">
        {audioUrl && (
          <div className="px-8 pt-6">
            <div className="bg-navy-50 rounded-2xl p-3 flex items-center gap-4 border border-navy-100/50">
                 <div className="w-10 h-10 bg-brand-500 rounded-xl flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
                    <Volume2 size={18} />
                 </div>
                 <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-8 bg-transparent" />
            </div>
          </div>
        )}
        
        <div className="p-8 border-b border-navy-50 bg-gradient-to-br from-teal-50/50 via-white to-transparent">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-teal-600 rounded-2xl text-white shadow-lg shadow-teal-600/20">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-xl font-extrabold text-navy-900 tracking-tight">{report.report_type || "Lab Analysis"}</h3>
                <div className="flex items-center gap-2 mt-1">
                    <span className="px-2 py-0.5 bg-teal-50 text-teal-700 text-[10px] font-bold uppercase rounded-lg border border-teal-100">Legacy Format</span>
                </div>
              </div>
            </div>
            <button 
              onClick={handleDownload}
              disabled={downloading}
              className="group flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-white border border-navy-100 text-sm font-bold text-navy-600 hover:text-brand-600 hover:border-brand-200 hover:bg-brand-50 transition-all shadow-sm active:scale-95"
            >
              {downloading ? (
                <Loader2 className="h-4 w-4 animate-spin text-brand-600" />
              ) : (
                <Download className="h-4 w-4 group-hover:-translate-y-0.5 transition-transform" />
              )}
              {downloading ? 'Preparing...' : 'Export PDF'}
            </button>
          </div>
          <p className="text-navy-700 text-base leading-relaxed font-medium">{report.interpretation}</p>
        </div>

        <div className="p-8">
          <h4 className="text-xs font-bold text-navy-400 uppercase tracking-widest mb-6 flex items-center gap-2">
            <Activity className="h-4 w-4 text-brand-500" />
            Detected Lab Markers
          </h4>
          <div className="overflow-hidden rounded-3xl border border-navy-100 shadow-sm">
            <table className="w-full text-sm text-left border-collapse">
              <thead className="bg-navy-50/50">
                <tr>
                  <th className="px-6 py-4 font-bold text-navy-900 uppercase tracking-wider text-[10px]">Marker</th>
                  <th className="px-6 py-4 font-bold text-navy-900 uppercase tracking-wider text-[10px]">Value</th>
                  <th className="px-6 py-4 font-bold text-navy-900 uppercase tracking-wider text-[10px]">Reference</th>
                  <th className="px-6 py-4 font-bold text-navy-900 uppercase tracking-wider text-[10px]">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-50">
                {report.key_values?.map((kv, i) => (
                  <tr key={i} className="hover:bg-brand-50/30 transition-colors">
                    <td className="px-6 py-4 font-bold text-navy-900">{kv.marker}</td>
                    <td className="px-6 py-4 text-navy-900 font-bold">{kv.value}</td>
                    <td className="px-6 py-4 text-navy-500 font-medium">{kv.range}</td>
                    <td className="px-6 py-4">
                      <span className={clsx(
                        "px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider",
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

          <div className="mt-8 bg-brand-50 rounded-3xl p-6 border border-brand-100 group">
            <h4 className="text-brand-900 font-bold text-sm mb-3 flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              Primary Recommendation
            </h4>
            <p className="text-brand-800 text-sm leading-relaxed font-medium">{report.recommendation}</p>
          </div>
        </div>

        <div className="px-8 py-5 bg-navy-50/50 border-t border-navy-100 flex items-start gap-4">
          <Info className="h-5 w-5 text-navy-300 mt-0.5 shrink-0" />
          <p className="text-[11px] text-navy-400 leading-relaxed font-medium">{report.disclaimer}</p>
        </div>
      </div>
    );
  }

  // Handle Clarification Questions (Triage Mode)
  if (report?.type === 'clarification_questions') {
    return (
      <div className="bg-brand-50 rounded-[2rem] p-8 shadow-premium border border-brand-100 animate-slide-up">
         {audioUrl && (
            <div className="mb-6 bg-white p-3 rounded-2xl flex items-center gap-4 border border-brand-100 shadow-sm">
                <div className="w-10 h-10 bg-brand-500 rounded-xl flex items-center justify-center text-white">
                    <Volume2 size={18} />
                </div>
                <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-8" />
            </div>
         )}
         <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-white rounded-2xl shadow-sm border border-brand-100">
                <HelpCircle className="h-6 w-6 text-brand-600" />
            </div>
            <div>
                <h3 className="text-xl font-extrabold text-navy-900 tracking-tight">Clarification Needed</h3>
                <p className="text-xs font-bold text-brand-600 uppercase tracking-widest mt-1">Assessment in progress</p>
            </div>
         </div>
         <p className="text-navy-700 mb-8 leading-relaxed font-medium text-base">{report.context}</p>
         <div className="space-y-4">
            {report.questions && report.questions.map((q, i) => (
                <div key={i} className="bg-white p-5 rounded-[1.25rem] border border-brand-100 text-navy-900 font-bold shadow-sm flex gap-4 hover:border-brand-300 transition-colors group">
                    <span className="flex-shrink-0 w-8 h-8 bg-brand-50 text-brand-600 rounded-xl flex items-center justify-center text-sm font-extrabold group-hover:bg-brand-600 group-hover:text-white transition-colors">{i + 1}</span>
                    <span className="mt-1">{q}</span>
                </div>
            ))}
         </div>
         <div className="mt-8 flex items-center gap-3 px-2">
            <div className="w-2 h-2 bg-brand-500 rounded-full animate-pulse" />
            <p className="text-[10px] text-brand-600 font-extrabold uppercase tracking-[0.2em]">Awaiting your response to continue</p>
         </div>
      </div>
    );
  }

  // Handle Medical Image Analysis (Strict Format)
  if (report?.input_type === 'medical_image') {
    if (report.status === 'HITL_ESCALATED') {
      return (
        <div className="bg-orange-50 rounded-[2rem] p-8 shadow-premium border border-orange-200 animate-slide-up">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-white rounded-2xl shadow-sm border border-orange-200">
              <AlertTriangle className="h-6 w-6 text-orange-600" />
            </div>
            <div>
              <h3 className="text-xl font-extrabold text-navy-900 tracking-tight">Manual Review Required</h3>
              <p className="text-xs font-bold text-orange-600 uppercase tracking-widest mt-1">Safety Escalation</p>
            </div>
          </div>
          <p className="text-navy-700 mb-6 leading-relaxed font-medium text-base">{report.message}</p>
          <div className="bg-white/50 p-4 rounded-2xl border border-orange-100 text-sm text-navy-600 italic">
            Reason: {report.reason}
          </div>
          <div className="mt-8 flex items-start gap-4 p-4 bg-orange-100/50 rounded-2xl border border-orange-200">
            <Info className="h-5 w-5 text-orange-600 mt-0.5 shrink-0" />
            <p className="text-xs text-orange-800 leading-relaxed font-medium">{report.disclaimer}</p>
          </div>
        </div>
      );
    }

    return (
      <div className="bg-white rounded-[2rem] shadow-premium border border-navy-100 overflow-hidden max-w-3xl animate-slide-up">
        {audioUrl && (
          <div className="px-8 pt-6">
            <div className="bg-navy-50 rounded-2xl p-3 flex items-center gap-4 border border-navy-100/50">
                 <div className="w-10 h-10 bg-brand-500 rounded-xl flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
                    <Volume2 size={18} />
                 </div>
                 <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-8 bg-transparent" />
            </div>
          </div>
        )}

        <div className="p-8 border-b border-navy-50 bg-gradient-to-br from-teal-50/50 via-white to-transparent">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-teal-600 rounded-2xl text-white shadow-lg shadow-teal-600/20">
                <ImageIcon className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-xl font-extrabold text-navy-900 tracking-tight">Visual Health Analysis</h3>
                <div className="flex items-center gap-2 mt-1">
                  <SeverityBadge level={report.severity || "MODERATE"} />
                </div>
              </div>
            </div>
            <button 
              onClick={handleDownload}
              disabled={downloading}
              className="group flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-white border border-navy-100 text-sm font-bold text-navy-600 hover:text-brand-600 hover:border-brand-200 hover:bg-brand-50 transition-all shadow-sm active:scale-95"
            >
              {downloading ? (
                <span className="w-4 h-4 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"></span>
              ) : (
                <Download className="h-4 w-4 group-hover:-translate-y-0.5 transition-transform" />
              )}
              {downloading ? 'Preparing...' : 'Export PDF'}
            </button>
          </div>
          <div className="flex flex-wrap gap-2.5 mt-2">
            {report.observations?.map((obs, i) => (
              <span key={i} className="px-4 py-2 bg-white border border-teal-100 text-teal-700 text-xs font-bold rounded-xl shadow-sm">
                {obs}
              </span>
            ))}
          </div>
        </div>

        <div className="p-8 space-y-8">
          <div>
            <h4 className="text-xs font-bold text-navy-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <Brain className="h-4 w-4 text-brand-500" />
              Clinical Considerations
            </h4>
            <ul className="space-y-3">
              {report.possible_conditions?.map((cond, i) => (
                <li key={i} className="flex items-start gap-3 text-navy-700 font-medium">
                  <div className="w-1.5 h-1.5 rounded-full bg-brand-500 mt-2 shrink-0 shadow-sm shadow-brand-500/50" />
                  {cond}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-orange-50 rounded-3xl p-6 border border-orange-100 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
                <Utensils size={64} />
            </div>
            <h4 className="text-orange-900 font-bold text-sm mb-3 flex items-center gap-2 relative z-10">
              <Utensils className="h-5 w-5" />
              General Care Advice
            </h4>
            <p className="text-orange-800 text-sm leading-relaxed font-medium relative z-10">{report.general_advice}</p>
          </div>
        </div>

        <div className="px-8 py-5 bg-navy-50/50 border-t border-navy-100 flex items-start gap-4">
          <Info className="h-5 w-5 text-navy-300 mt-0.5 shrink-0" />
          <p className="text-[11px] text-navy-400 leading-relaxed font-medium">{report.disclaimer}</p>
        </div>
      </div>
    );
  }

  // Handle Legacy or Error Formats
  if (!report || !report.summary) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <p className="text-gray-700 leading-relaxed">{typeof report === 'string' ? report : JSON.stringify(report)}</p>
      </div>
    );
  }

  // Normalize Data Structure (Backwards Compatibility)
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
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden max-w-3xl animate-in fade-in slide-in-from-bottom-4">
      {audioUrl && (
          <div className="px-6 pt-4">
            <div className="bg-gray-50 rounded-lg p-2 flex items-center gap-3">
                 <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center text-primary">
                    <Volume2 size={16} />
                 </div>
                 <audio controls src={`http://localhost:8000${audioUrl}`} className="w-full h-8 bg-transparent" />
            </div>
          </div>
        )}
      
      {/* Header */}
      <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-lg font-semibold text-gray-900">Health Assessment</h3>
              <button 
                onClick={handleDownload}
                disabled={downloading}
                className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-gray-200 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:text-primary transition-colors shadow-sm"
              >
                {downloading ? <span className="w-3 h-3 border-2 border-gray-400 border-t-primary rounded-full animate-spin"></span> : <Download className="h-3.5 w-3.5" />}
                {downloading ? 'Generating...' : 'PDF'}
              </button>
            </div>
            <p className="text-gray-600 text-sm leading-relaxed mb-4">{report.summary}</p>
            
            {/* Confidence Bar */}
            {confidence > 0 && <ConfidenceBar score={confidence} reason={uncertainty} />}
          </div>
          
          <div className="shrink-0 flex flex-col items-end gap-2">
            <SeverityBadge level={severity} />
          </div>
        </div>
      </div>

      {/* Recommendations Grid */}
      <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Specialist Suggestion (New Feature) */}
        {specialist && (
            <div className="col-span-1 md:col-span-2 bg-teal-50 rounded-xl p-5 border border-teal-100">
                <div className="flex items-start gap-4">
                    <div className="p-3 bg-teal-100 rounded-full text-teal-600">
                        <UserIcon className="w-6 h-6" />
                    </div>
                    <div>
                        <h4 className="text-teal-900 font-semibold flex items-center gap-2">
                            Consultation Suggested: {specialist.type}
                            <span className="text-xs px-2 py-0.5 bg-white rounded-full border border-teal-200 text-teal-600 uppercase tracking-wide">
                                {specialist.urgency}
                            </span>
                        </h4>
                        <p className="text-sm text-teal-700 mt-1">{specialist.reason}</p>
                        <p className="text-[10px] text-teal-500 mt-2 uppercase tracking-wider font-medium">
                            Advisory Only • Not a Referral
                        </p>
                    </div>
                </div>
            </div>
        )}

        {/* Google-Level Explainability Panel */}
        {explanation.reasoning && (
          <div className="bg-slate-50 rounded-xl border border-slate-100 overflow-hidden">
            <button 
              onClick={() => setShowExplanation(!showExplanation)}
              className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-100 transition-colors"
            >
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                <Brain className="h-4 w-4 text-primary" />
                Why this advice? (AI Logic)
              </div>
              <span className="text-xs text-primary font-medium">{showExplanation ? "Hide" : "Show"}</span>
            </button>
            
            {showExplanation && (
              <div className="p-4 pt-0 border-t border-slate-100 bg-white">
                <div className="mt-3 space-y-3 text-sm text-slate-600">
                  <p><span className="font-medium text-slate-800">Reasoning:</span> {explanation.reasoning}</p>
                  {explanation.history_factor && (
                     <p><span className="font-medium text-slate-800">History Context:</span> {explanation.history_factor}</p>
                  )}
                  {explanation.profile_factor && (
                     <p><span className="font-medium text-slate-800">Profile Impact:</span> {explanation.profile_factor}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Immediate Action (If Critical) */}
        {immediate_action && (
          <div className="bg-blue-50/50 rounded-xl p-4 border border-blue-100 flex items-start gap-3">
             <ShieldCheck className="h-5 w-5 text-blue-600 mt-0.5" />
             <div>
                <h4 className="font-medium text-blue-900 text-sm mb-1">Recommended Action</h4>
                <p className="text-blue-800 text-sm">{immediate_action}</p>
             </div>
          </div>
        )}

        {/* Possible Conditions */}
        {report.possible_causes && report.possible_causes.length > 0 && (
          <div>
            <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3">
              <Stethoscope className="h-4 w-4 text-primary" />
              Possible Conditions (Not a diagnosis)
            </h4>
            <div className="flex flex-wrap gap-2">
              {report.possible_causes.map((condition, idx) => (
                <span key={idx} className="inline-flex items-center px-3 py-1 rounded-lg bg-gray-100 text-gray-700 text-sm border border-gray-200">
                  {condition}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Lifestyle Recommendations */}
        {lifestyle_advice.length > 0 && (
          <div>
            <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              Lifestyle Advice
            </h4>
            <ul className="space-y-2">
              {lifestyle_advice.map((action, idx) => (
                <li key={idx} className="flex items-start gap-3 text-sm text-gray-600">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 mt-2 shrink-0" />
                  {action}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Food Recommendations */}
        {food_advice.length > 0 && (
          <div>
            <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-900 mb-3">
              <Utensils className="h-4 w-4 text-orange-500" />
              Personalized Nutrition
            </h4>
            <ul className="space-y-2">
              {food_advice.map((item, idx) => (
                <li key={idx} className="flex items-start gap-3 text-sm text-gray-600">
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-300 mt-2 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Trusted Sources (RAG) */}
        {report.knowledge_sources && report.knowledge_sources.length > 0 && (
          <div className="col-span-1 md:col-span-2 mt-2 pt-4 border-t border-gray-100">
             <h4 className="flex items-center gap-2 text-sm font-semibold text-blue-900 mb-3">
              <FileText className="h-4 w-4 text-blue-600" />
              Trusted Medical Sources
            </h4>
            <div className="grid gap-3 md:grid-cols-2">
                {report.knowledge_sources.map((src, idx) => (
                    <div key={idx} className="bg-blue-50 rounded-lg p-3 border border-blue-100">
                        <p className="text-xs font-bold text-blue-800 mb-1">{src.source || "Source"}</p>
                        <p className="text-xs text-blue-600 leading-snug">{src.description}</p>
                    </div>
                ))}
            </div>
          </div>
        )}
      </div>

      {/* Feedback Section */}
      <div className="px-6 pb-2 flex items-center justify-end gap-2">
        <span className="text-xs text-gray-400">Was this helpful?</span>
        <button 
            onClick={() => handleFeedback('positive')}
            disabled={feedbackGiven}
            className={`p-1.5 rounded-full transition-colors ${feedbackGiven === 'positive' ? 'bg-green-100 text-green-600' : 'hover:bg-gray-100 text-gray-400'}`}
        >
            <ThumbsUp className="h-4 w-4" />
        </button>
        <button 
            onClick={() => handleFeedback('negative')}
            disabled={feedbackGiven}
            className={`p-1.5 rounded-full transition-colors ${feedbackGiven === 'negative' ? 'bg-red-100 text-red-600' : 'hover:bg-gray-100 text-gray-400'}`}
        >
            <ThumbsDown className="h-4 w-4" />
        </button>
      </div>

      {/* Disclaimer Footer */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex items-start gap-3">
        <Info className="h-4 w-4 text-gray-400 mt-0.5 shrink-0" />
        <p className="text-xs text-gray-500 leading-relaxed">
          {report.disclaimer || "This AI provides preliminary guidance only and is not a substitute for professional medical advice."}
        </p>
      </div>
    </div>
  );
};

export default ReportCard;
