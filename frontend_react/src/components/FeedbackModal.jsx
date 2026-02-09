import React, { useState } from 'react';
import { X, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

const FeedbackModal = ({ isOpen, onClose, onSubmit }) => {
  const [selectedReason, setSelectedReason] = useState('');
  const [optionalText, setOptionalText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const reasons = [
    "The answer was too complex",
    "The answer was incorrect",
    "The answer was too generic",
    "The answer was incomplete",
    "The answer was irrelevant",
    "Safety concern / harmful advice",
    "Other"
  ];

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedReason) return;
    
    setIsSubmitting(true);
    try {
      await onSubmit(selectedReason, optionalText);
      onClose();
    } catch (error) {
      console.error("Submission failed", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-navy-900/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl overflow-hidden animate-slide-up border border-navy-100">
        <div className="px-6 py-4 border-b border-navy-50 flex items-center justify-between bg-navy-50/30">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-rose-100 rounded-lg text-rose-600">
              <AlertCircle size={18} />
            </div>
            <h3 className="text-lg font-black text-navy-900 tracking-tight">Provide Feedback</h3>
          </div>
          <button 
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-navy-100 text-navy-400 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-2">
            <label className="text-[11px] font-black text-navy-400 uppercase tracking-widest">
              Why was this not helpful?
            </label>
            <div className="grid grid-cols-1 gap-2">
              {reasons.map((reason) => (
                <button
                  key={reason}
                  type="button"
                  onClick={() => setSelectedReason(reason)}
                  className={clsx(
                    "w-full text-left px-4 py-3 rounded-xl border text-sm font-bold transition-all active:scale-[0.98]",
                    selectedReason === reason 
                      ? "bg-brand-50 border-brand-500 text-brand-900 shadow-sm" 
                      : "bg-white border-navy-100 text-navy-600 hover:border-navy-300 hover:bg-navy-50/30"
                  )}
                >
                  {reason}
                </button>
              ))}
            </div>
          </div>

          {selectedReason === 'Other' && (
            <div className="space-y-2 animate-fade-in">
              <label className="text-[11px] font-black text-navy-400 uppercase tracking-widest">
                Additional details
              </label>
              <textarea
                value={optionalText}
                onChange={(e) => setOptionalText(e.target.value)}
                placeholder="Please tell us what went wrong..."
                className="w-full h-24 p-4 rounded-xl border border-navy-100 text-sm font-medium focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none resize-none transition-all placeholder:text-navy-300"
              />
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={!selectedReason || isSubmitting}
              className={clsx(
                "w-full py-4 rounded-xl text-sm font-black uppercase tracking-widest transition-all shadow-lg active:scale-95 flex items-center justify-center gap-2",
                !selectedReason || isSubmitting
                  ? "bg-navy-100 text-navy-300 cursor-not-allowed"
                  : "bg-navy-900 text-white hover:bg-brand-600 shadow-navy-900/10"
              )}
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Submitting...
                </>
              ) : (
                "Submit Feedback"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FeedbackModal;
