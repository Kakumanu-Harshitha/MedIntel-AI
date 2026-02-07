import React, { useState, useEffect } from 'react';
import Header from '../components/Header';
import ReportCard from '../components/ReportCard';
import { dashboardService } from '../services/api';
import { Loader2, FileText, Calendar, Clock } from 'lucide-react';

const Reports = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await dashboardService.getHistory();
        // Filter for assistant messages that are valid JSON reports
        const reports = data.filter(msg => msg.role === 'assistant').map(msg => {
            try {
                const parsed = JSON.parse(msg.content);
                
                // Identify report types based on schema
                const isHealthReport = parsed.type === 'health_report' || !!parsed.health_information;
                const isMedicalAnalysis = parsed.type === 'medical_report_analysis' || !!parsed.test_analysis;
                const isLegacyMedical = parsed.input_type === 'medical_report' || !!parsed.interpretation;
                const isImageAnalysis = parsed.input_type === 'medical_image' || !!parsed.observations;
                const isGeneralReport = !!parsed.summary && (!!parsed.severity || !!parsed.risk_assessment);

                if (isHealthReport || isMedicalAnalysis || isLegacyMedical || isImageAnalysis || isGeneralReport) {
                    return parsed;
                }
                return null;
            } catch (e) {
                return null;
            }
        }).filter(Boolean);
        
        // We might want to reverse to show newest first if the API doesn't
        setHistory(reports.reverse());
      } catch (error) {
        console.error("Failed to fetch reports:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-brand-50 via-white to-navy-50 flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-12">
        <div className="mb-12 animate-fade-in">
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-brand-600 rounded-2xl text-white shadow-lg shadow-brand-600/20">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold text-navy-900 tracking-tight">Report History</h1>
              <p className="text-navy-400 font-bold text-xs uppercase tracking-widest mt-1">
                Your clinical assessment records
              </p>
            </div>
          </div>
          <p className="text-navy-500 text-lg max-w-2xl leading-relaxed">
            Access and manage your previous AI health assessments, laboratory analyses, and clinical recommendations.
          </p>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-12 h-12 border-4 border-navy-100 border-t-brand-600 rounded-full animate-spin" />
            <p className="text-navy-400 font-bold text-xs uppercase tracking-widest">Loading Records...</p>
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-[2.5rem] border border-navy-100 shadow-premium animate-fade-in">
            <div className="w-20 h-20 bg-navy-50 rounded-3xl flex items-center justify-center mx-auto mb-6">
              <FileText className="h-10 w-10 text-navy-200" />
            </div>
            <h3 className="text-xl font-extrabold text-navy-900 mb-2">No Reports Found</h3>
            <p className="text-navy-400 max-w-xs mx-auto mb-8 font-medium">Start a new session with our AI assistant to generate your first clinical report.</p>
            <button 
              onClick={() => window.location.href = '/chat'}
              className="px-8 py-3.5 bg-brand-600 text-white font-bold rounded-2xl shadow-lg shadow-brand-600/20 hover:bg-brand-700 transition-all active:scale-95"
            >
              Start New Assessment
            </button>
          </div>
        ) : (
          <div className="grid gap-10">
            {history.map((report, idx) => (
              <div key={idx} className="group relative">
                <div className="absolute -left-4 top-0 bottom-0 w-1 bg-navy-100 rounded-full group-hover:bg-brand-500 transition-colors" />
                <div className="flex items-center justify-between mb-4 px-2">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-navy-50 rounded-xl text-navy-400">
                            <Calendar className="h-4 w-4" />
                        </div>
                        <span className="text-sm font-bold text-navy-900">Record #{history.length - idx}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-extrabold text-navy-300 uppercase tracking-widest">
                        <Clock className="h-3.5 w-3.5" />
                        <span>Archived Report</span>
                    </div>
                </div>
                <div className="transition-all duration-300 hover:translate-x-1">
                    <ReportCard data={report} />
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <div className="py-12 border-t border-navy-100/50 bg-white/30 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-6">
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-navy-300 uppercase tracking-[0.2em]">Data Security</span>
                    <span className="text-sm font-bold text-navy-900">End-to-End Encrypted</span>
                </div>
                <div className="w-px h-8 bg-navy-100" />
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-navy-300 uppercase tracking-[0.2em]">Compliance</span>
                    <span className="text-sm font-bold text-navy-900">Clinical Grade AI</span>
                </div>
            </div>
            <p className="text-[11px] text-navy-400 font-medium max-w-xs text-center md:text-right">
                All reports are generated by AI and should be reviewed by a qualified healthcare professional.
            </p>
        </div>
      </div>
    </div>
  );
};

export default Reports;