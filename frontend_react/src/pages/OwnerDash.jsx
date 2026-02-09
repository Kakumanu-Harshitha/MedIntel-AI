import React, { useState, useEffect } from 'react';
import Header from '../components/Header';
import { 
  Activity, 
  Users, 
  MessageSquare, 
  AlertTriangle, 
  Shield, 
  History, 
  ToggleLeft, 
  ChevronRight,
  TrendingUp,
  Smile,
  Cpu,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Eye,
  X
} from 'lucide-react';
import { ownerService } from '../services/api';
import clsx from 'clsx';

const StatCard = ({ icon: Icon, label, value, subValue, trend, color = "brand" }) => (
  <div className="bg-white p-6 rounded-3xl border border-navy-100 shadow-premium flex flex-col gap-4">
    <div className="flex items-center justify-between">
      <div className={clsx("p-3 rounded-2xl", {
        "bg-brand-50 text-brand-600": color === "brand",
        "bg-emerald-50 text-emerald-600": color === "emerald",
        "bg-amber-50 text-amber-600": color === "amber",
        "bg-rose-50 text-rose-600": color === "rose",
        "bg-indigo-50 text-indigo-600": color === "indigo",
      })}>
        <Icon className="h-6 w-6" />
      </div>
      {trend && (
        <span className={clsx("text-xs font-bold px-2 py-1 rounded-lg", 
          trend > 0 ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600"
        )}>
          {trend > 0 ? '+' : ''}{trend}%
        </span>
      )}
    </div>
    <div>
      <p className="text-[10px] font-bold text-navy-400 uppercase tracking-[0.2em] mb-1">{label}</p>
      <div className="flex items-baseline gap-2">
        <h3 className="text-2xl font-extrabold text-navy-900">{value}</h3>
        {subValue && <span className="text-sm font-medium text-navy-400">{subValue}</span>}
      </div>
    </div>
  </div>
);

const OwnerDash = () => {
  const [activeTab, setActiveTab] = useState('health');
  const [metrics, setMetrics] = useState({
    health: null,
    satisfaction: null,
    model: null,
    security: null,
    hitl: null,
    toggles: []
  });
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedEscalation, setSelectedEscalation] = useState(null);
  const [isAddToggleModalOpen, setIsAddToggleModalOpen] = useState(false);
  const [newToggleData, setNewToggleData] = useState({ key: '', value: 'OFF' });
  const [isSubmittingToggle, setIsSubmittingToggle] = useState(false);

  useEffect(() => {
    const fetchAllData = async () => {
      setLoading(true);
      try {
        const [health, satisfaction, model, security, hitl, toggles, auditLogs] = await Promise.all([
          ownerService.getHealthMetrics(),
          ownerService.getSatisfactionMetrics(),
          ownerService.getModelMetrics(),
          ownerService.getSecurityMetrics(),
          ownerService.getHitlMetrics(),
          ownerService.getToggles(),
          ownerService.getAuditLogs({ limit: 20 })
        ]);

        setMetrics({ health, satisfaction, model, security, hitl, toggles });
        setLogs(auditLogs.logs || []);
      } catch (err) {
        console.error("Failed to fetch owner metrics", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, []);

  const handleToggle = async (key, currentValue) => {
    const newValue = currentValue === 'ON' ? 'OFF' : 'ON';
    try {
      await ownerService.updateToggle(key, newValue);
      const updatedToggles = await ownerService.getToggles();
      setMetrics(prev => ({ ...prev, toggles: updatedToggles }));
    } catch (err) {
      console.error("Failed to update toggle", err);
    }
  };

  const handleAddToggle = async (e) => {
    e.preventDefault();
    if (!newToggleData.key.trim()) return;
    
    setIsSubmittingToggle(true);
    try {
      await ownerService.updateToggle(newToggleData.key, newToggleData.value);
      const updatedToggles = await ownerService.getToggles();
      setMetrics(prev => ({ ...prev, toggles: updatedToggles }));
      setIsAddToggleModalOpen(false);
      setNewToggleData({ key: '', value: 'OFF' });
    } catch (err) {
      console.error("Failed to add toggle", err);
    } finally {
      setIsSubmittingToggle(false);
    }
  };

  const tabs = [
    { id: 'health', name: 'System Health', icon: Activity },
    { id: 'satisfaction', name: 'User Satisfaction', icon: Smile },
    { id: 'model', name: 'AI Models', icon: Cpu },
    { id: 'security', name: 'Security', icon: Shield },
    { id: 'hitl', name: 'HITL Monitoring', icon: Eye },
    { id: 'logs', name: 'Audit Logs', icon: History },
    { id: 'toggles', name: 'System Toggles', icon: ToggleLeft },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
          <div>
            <h1 className="text-3xl font-extrabold text-navy-900 tracking-tight">Owner Dashboard</h1>
            <p className="text-navy-400 font-bold text-xs uppercase tracking-widest mt-1">
              Enterprise Control Center & System Intelligence
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button 
              onClick={() => window.location.reload()}
              className="p-3 bg-white border border-navy-100 rounded-2xl text-navy-600 hover:text-brand-600 shadow-sm transition-all active:scale-95"
            >
              <RefreshCw className="h-5 w-5" />
            </button>
            <div className="h-10 w-px bg-navy-200 hidden md:block" />
            <div className="bg-emerald-50 text-emerald-600 px-4 py-2 rounded-2xl border border-emerald-100 flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              <span className="text-xs font-bold uppercase tracking-wider">System Operational</span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex overflow-x-auto pb-4 gap-2 no-scrollbar mb-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                "px-6 py-3 rounded-2xl text-sm font-bold transition-all flex items-center gap-3 shrink-0 whitespace-nowrap border",
                activeTab === tab.id 
                  ? "bg-brand-600 text-white border-brand-600 shadow-lg shadow-brand-600/20" 
                  : "bg-white text-navy-500 border-navy-100 hover:border-navy-200 hover:text-navy-900"
              )}
            >
              <tab.icon className="h-4 w-4" />
              {tab.name}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="w-12 h-12 border-4 border-navy-100 border-t-brand-600 rounded-full animate-spin" />
            <p className="text-navy-400 font-bold text-xs uppercase tracking-widest">Aggregating Metrics...</p>
          </div>
        ) : (
          <div className="animate-fade-in">
            {activeTab === 'health' && metrics.health && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <StatCard icon={Users} label="Total Users" value={metrics.health.total_users} color="brand" />
                <StatCard icon={Activity} label="Active Today" value={metrics.health.active_today} color="emerald" />
                <StatCard icon={TrendingUp} label="Active Weekly" value={metrics.health.active_week} color="indigo" />
                <StatCard icon={MessageSquare} label="Queries (24h)" value={metrics.health.total_queries} color="brand" />
                <StatCard icon={AlertTriangle} label="Error Rate (24h)" value={`${metrics.health.error_rate}%`} color="rose" />
                <StatCard icon={Eye} label="HITL Escalations" value={metrics.health.hitl_escalations} color="amber" />
              </div>
            )}

            {activeTab === 'satisfaction' && metrics.satisfaction && (
              <div className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <StatCard icon={Smile} label="Helpfulness Rate" value={`${metrics.satisfaction.helpfulness_rate}%`} color="emerald" />
                  <StatCard icon={MessageSquare} label="Total Feedback" value={metrics.satisfaction.total_feedback} color="brand" />
                  <StatCard icon={TrendingUp} label="Avg Confidence" value={metrics.satisfaction.avg_confidence?.helpful || 0} subValue="for helpful" color="indigo" />
                </div>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Negative Feedback Breakdown */}
                  <div className="bg-white p-8 rounded-[2.5rem] border border-navy-100 shadow-premium">
                    <h3 className="text-lg font-extrabold text-navy-900 mb-6">Negative Feedback Breakdown</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {Object.entries(metrics.satisfaction.reasons_breakdown).length > 0 ? (
                        Object.entries(metrics.satisfaction.reasons_breakdown).map(([reason, count]) => (
                          <div key={reason} className="p-4 bg-slate-50 rounded-2xl border border-navy-50">
                            <p className="text-[10px] font-bold text-navy-400 uppercase tracking-wider mb-1">{reason}</p>
                            <p className="text-xl font-black text-navy-900">{count}</p>
                          </div>
                        ))
                      ) : (
                        <div className="col-span-full py-10 text-center text-navy-400 font-bold text-xs uppercase tracking-widest">
                          No negative feedback recorded
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Recent Feedback List */}
                  <div className="bg-white rounded-[2.5rem] border border-navy-100 shadow-premium overflow-hidden">
                    <div className="p-8 border-b border-navy-50">
                      <h3 className="text-lg font-extrabold text-navy-900">Recent User Feedback</h3>
                    </div>
                    <div className="max-h-[400px] overflow-y-auto no-scrollbar">
                      <div className="divide-y divide-navy-50">
                        {metrics.satisfaction.recent_feedback?.length > 0 ? (
                          metrics.satisfaction.recent_feedback.map((f, idx) => (
                            <div key={idx} className="p-6 hover:bg-slate-50 transition-colors">
                              <div className="flex items-center justify-between mb-2">
                                <span className={clsx(
                                  "px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest border",
                                  f.rating === 'positive' ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-rose-50 text-rose-600 border-rose-100"
                                )}>
                                  {f.rating}
                                </span>
                                <span className="text-[10px] font-bold text-navy-400">
                                  {new Date(f.timestamp).toLocaleString()}
                                </span>
                              </div>
                              <p className="text-sm font-medium text-navy-900 mb-1">{f.comment}</p>
                              <p className="text-[10px] font-bold text-navy-400 uppercase tracking-widest">
                                Msg ID: <span className="font-mono">{f.messageId}</span>
                              </p>
                            </div>
                          ))
                        ) : (
                          <div className="p-10 text-center text-navy-400 font-bold text-xs uppercase tracking-widest">
                            No recent feedback available
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'model' && metrics.model && (
              <div className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <StatCard icon={Cpu} label="Total Detections" value={metrics.model.total_detections} color="brand" />
                  <StatCard icon={RefreshCw} label="Fallback Rate" value={`${metrics.model.fallback_rate}%`} color="rose" />
                  <StatCard icon={Activity} label="Primary Model" value="Llama-3.3-70b" subValue="99.4% Success" color="emerald" />
                </div>
                <div className="bg-white p-8 rounded-[2.5rem] border border-navy-100 shadow-premium">
                  <h3 className="text-lg font-extrabold text-navy-900 mb-6">Model Usage Distribution</h3>
                  <div className="space-y-4">
                    {Object.entries(metrics.model.model_counts).map(([model, count]) => (
                      <div key={model} className="flex items-center gap-4">
                        <div className="w-32 text-sm font-bold text-navy-600 truncate">{model}</div>
                        <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-brand-500 rounded-full" 
                            style={{ width: `${(count / metrics.model.total_detections) * 100}%` }}
                          />
                        </div>
                        <div className="w-12 text-sm font-black text-navy-900 text-right">{count}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'security' && metrics.security && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard icon={Shield} label="Password Resets" value={metrics.security.password_resets} color="indigo" />
                <StatCard icon={AlertTriangle} label="Failed Logins" value={metrics.security.failed_logins} color="amber" />
                <StatCard icon={XCircle} label="OTP Failures" value={metrics.security.otp_failures} color="rose" />
                <StatCard icon={Shield} label="Suspicious Spikes" value={metrics.security.suspicious_activity ? "YES" : "NO"} color={metrics.security.suspicious_activity ? "rose" : "emerald"} />
              </div>
            )}

            {activeTab === 'hitl' && metrics.hitl && (
              <div className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <StatCard icon={Eye} label="Total Escalations" value={metrics.hitl.total_escalations} color="amber" />
                  <StatCard icon={TrendingUp} label="Escalation Rate" value={`${metrics.hitl.escalation_rate}%`} color="indigo" />
                  <StatCard icon={Users} label="Queue Status" value="Healthy" subValue="< 2m wait" color="emerald" />
                </div>
                <div className="bg-white rounded-[2.5rem] border border-navy-100 shadow-premium overflow-hidden">
                  <div className="p-8 border-b border-navy-50">
                    <h3 className="text-lg font-extrabold text-navy-900">Recent Escalations</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left">
                      <thead className="bg-slate-50 text-[10px] font-bold text-navy-400 uppercase tracking-widest">
                        <tr>
                          <th className="px-8 py-4">Timestamp</th>
                          <th className="px-8 py-4">Reason</th>
                          <th className="px-8 py-4">User ID</th>
                          <th className="px-8 py-4">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-navy-50">
                        {metrics.hitl.recent_escalations.map((esc) => (
                          <tr key={esc.id} className="hover:bg-slate-50 transition-colors">
                            <td className="px-8 py-5 text-sm font-medium text-navy-500">
                              {new Date(esc.timestamp).toLocaleString()}
                            </td>
                            <td className="px-8 py-5">
                              <span className="px-3 py-1 bg-amber-50 text-amber-600 rounded-lg text-xs font-bold border border-amber-100">
                                {esc.reason}
                              </span>
                            </td>
                            <td className="px-8 py-5 text-sm font-black text-navy-900">#{esc.user_id}</td>
                            <td className="px-8 py-5">
                              <button 
                                onClick={() => setSelectedEscalation(esc)}
                                className="text-brand-600 hover:text-brand-700 font-bold text-xs uppercase tracking-wider flex items-center gap-1 transition-colors"
                              >
                                Review <ChevronRight className="h-3 w-3" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'logs' && (
              <div className="bg-white rounded-[2.5rem] border border-navy-100 shadow-premium overflow-hidden">
                <div className="p-8 border-b border-navy-50 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <h3 className="text-lg font-extrabold text-navy-900">Enterprise Audit Logs</h3>
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-navy-300" />
                      <input 
                        type="text" 
                        placeholder="Search logs..." 
                        className="pl-10 pr-4 py-2 bg-slate-50 border border-navy-100 rounded-xl text-sm focus:outline-none focus:border-brand-300 transition-all"
                      />
                    </div>
                    <button className="p-2 bg-slate-50 border border-navy-100 rounded-xl text-navy-400 hover:text-navy-900">
                      <Filter className="h-5 w-5" />
                    </button>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead className="bg-slate-50 text-[10px] font-bold text-navy-400 uppercase tracking-widest">
                      <tr>
                        <th className="px-8 py-4">Event</th>
                        <th className="px-8 py-4">User</th>
                        <th className="px-8 py-4">Status</th>
                        <th className="px-8 py-4">Source</th>
                        <th className="px-8 py-4">Time</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-navy-50">
                      {logs.map((log) => (
                        <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-8 py-5">
                            <div className="flex flex-col">
                              <span className="text-sm font-black text-navy-900">{log.action}</span>
                              <span className="text-[10px] text-navy-400 font-mono">{log.log_id}</span>
                            </div>
                          </td>
                          <td className="px-8 py-5 text-sm font-bold text-navy-600">
                            {log.user_id ? `User #${log.user_id}` : 'System'}
                          </td>
                          <td className="px-8 py-5">
                            <span className={clsx(
                              "px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest border",
                              log.status === 'SUCCESS' ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-rose-50 text-rose-600 border-rose-100"
                            )}>
                              {log.status}
                            </span>
                          </td>
                          <td className="px-8 py-5 text-xs font-bold text-navy-400 uppercase tracking-widest">
                            {log.source}
                          </td>
                          <td className="px-8 py-5 text-sm font-medium text-navy-500">
                            {new Date(log.timestamp).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'toggles' && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {metrics.toggles.map((toggle) => (
                  <div key={toggle.id} className="bg-white p-8 rounded-[2.5rem] border border-navy-100 shadow-premium flex items-center justify-between group">
                    <div>
                      <h4 className="text-sm font-black text-navy-900 mb-1 group-hover:text-brand-600 transition-colors">{toggle.key}</h4>
                      <p className="text-[10px] font-bold text-navy-400 uppercase tracking-wider">
                        Last Updated: {new Date(toggle.updated_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button 
                      onClick={() => handleToggle(toggle.key, toggle.value)}
                      className={clsx(
                        "w-14 h-8 rounded-full relative transition-all duration-300",
                        toggle.value === 'ON' ? "bg-emerald-500" : "bg-slate-200"
                      )}
                    >
                      <div className={clsx(
                        "absolute top-1 w-6 h-6 bg-white rounded-full shadow-md transition-all duration-300",
                        toggle.value === 'ON' ? "right-1" : "left-1"
                      )} />
                    </button>
                  </div>
                ))}
                {/* Manual Add Toggle Card */}
                <div 
                  onClick={() => setIsAddToggleModalOpen(true)}
                  className="bg-white p-8 rounded-[2.5rem] border border-dashed border-navy-200 flex items-center justify-center cursor-pointer hover:bg-slate-50 transition-all group"
                >
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-10 h-10 rounded-2xl bg-slate-100 flex items-center justify-center text-navy-400 group-hover:bg-brand-50 group-hover:text-brand-600 transition-all">
                      <ToggleLeft className="h-5 w-5" />
                    </div>
                    <span className="text-xs font-bold text-navy-400 uppercase tracking-widest group-hover:text-navy-900 transition-colors">Add New Toggle</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Escalation Review Modal */}
      {selectedEscalation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-2xl rounded-[2.5rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-8 border-b border-navy-50 flex items-center justify-between bg-slate-50">
              <div>
                <h3 className="text-xl font-extrabold text-navy-900">Review Escalation</h3>
                <p className="text-xs font-bold text-navy-400 uppercase tracking-widest mt-1">
                  Incident Details & System Metadata
                </p>
              </div>
              <button 
                onClick={() => setSelectedEscalation(null)}
                className="p-2 hover:bg-white rounded-xl text-navy-400 hover:text-navy-900 transition-all border border-transparent hover:border-navy-100"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            
            <div className="p-8 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-6 mb-8">
                <div className="p-4 bg-slate-50 rounded-2xl border border-navy-50">
                  <p className="text-[10px] font-bold text-navy-400 uppercase tracking-wider mb-1">User ID</p>
                  <p className="text-lg font-black text-navy-900">#{selectedEscalation.user_id}</p>
                </div>
                <div className="p-4 bg-slate-50 rounded-2xl border border-navy-50">
                  <p className="text-[10px] font-bold text-navy-400 uppercase tracking-wider mb-1">Timestamp</p>
                  <p className="text-lg font-black text-navy-900">
                    {new Date(selectedEscalation.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>

              <div className="mb-8">
                <h4 className="text-xs font-bold text-navy-400 uppercase tracking-widest mb-3">Escalation Reason</h4>
                <div className="p-4 bg-amber-50 text-amber-700 rounded-2xl border border-amber-100 font-bold">
                  {selectedEscalation.reason}
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-navy-400 uppercase tracking-widest mb-3">Technical Metadata</h4>
                <div className="bg-navy-900 rounded-2xl p-6 overflow-x-auto shadow-inner">
                  <pre className="text-emerald-400 font-mono text-xs leading-relaxed">
                    {JSON.stringify(selectedEscalation.metadata, null, 2)}
                  </pre>
                </div>
              </div>
            </div>

            <div className="p-8 bg-slate-50 border-t border-navy-50 flex justify-end">
              <button 
                onClick={() => setSelectedEscalation(null)}
                className="px-8 py-3 bg-brand-600 text-white rounded-2xl font-bold text-sm shadow-lg shadow-brand-600/20 hover:bg-brand-700 transition-all active:scale-95"
              >
                Close Review
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Toggle Modal */}
      {isAddToggleModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-md rounded-[2.5rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-8 border-b border-navy-50 flex items-center justify-between bg-slate-50">
              <div>
                <h3 className="text-xl font-extrabold text-navy-900">Add New Toggle</h3>
                <p className="text-xs font-bold text-navy-400 uppercase tracking-widest mt-1">
                  Define a new system feature flag
                </p>
              </div>
              <button 
                onClick={() => setIsAddToggleModalOpen(false)}
                className="p-2 hover:bg-white rounded-xl text-navy-400 hover:text-navy-900 transition-all"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            
            <form onSubmit={handleAddToggle}>
              <div className="p-8 space-y-6">
                <div>
                  <label className="text-[10px] font-bold text-navy-400 uppercase tracking-[0.2em] mb-2 block">Toggle Key (Snake Case)</label>
                  <input 
                    type="text" 
                    required
                    placeholder="e.g. maintenance_mode" 
                    className="w-full px-5 py-4 bg-slate-50 border border-navy-100 rounded-2xl text-navy-900 font-bold focus:outline-none focus:border-brand-500 transition-all"
                    value={newToggleData.key}
                    onChange={(e) => setNewToggleData({ ...newToggleData, key: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-navy-400 uppercase tracking-[0.2em] mb-2 block">Initial Status</label>
                  <div className="flex gap-3">
                    {['OFF', 'ON'].map((status) => (
                      <button
                        key={status}
                        type="button"
                        onClick={() => setNewToggleData({ ...newToggleData, value: status })}
                        className={clsx(
                          "flex-1 py-4 rounded-2xl font-bold text-sm transition-all border-2",
                          newToggleData.value === status 
                            ? "bg-brand-50 border-brand-500 text-brand-600 shadow-sm" 
                            : "bg-white border-navy-50 text-navy-400 hover:border-navy-100"
                        )}
                      >
                        {status}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="p-8 bg-slate-50 border-t border-navy-50 flex gap-3">
                <button 
                  type="button"
                  onClick={() => setIsAddToggleModalOpen(false)}
                  className="flex-1 px-6 py-4 bg-white border border-navy-100 text-navy-600 rounded-2xl font-bold text-sm hover:bg-white/50 transition-all"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={isSubmittingToggle}
                  className="flex-1 px-6 py-4 bg-brand-600 text-white rounded-2xl font-bold text-sm shadow-lg shadow-brand-600/20 hover:bg-brand-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isSubmittingToggle ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    'Create Toggle'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default OwnerDash;
