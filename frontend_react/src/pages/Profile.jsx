import React, { useState, useEffect } from 'react';
import Header from '../components/Header';
import { profileService, securityService } from '../services/api';
import { 
  Save, User, Ruler, Weight, Activity, AlertCircle, 
  Lock, X, ShieldCheck, KeyRound, Eye, EyeOff,
  ChevronRight, Heart, Brain, Info
} from 'lucide-react';
import { clsx } from 'clsx';

const Profile = () => {
  const [profile, setProfile] = useState({
    patient_name: '',
    age: '',
    gender: 'Prefer not to say',
    weight_kg: '',
    height_cm: '',
    allergies: '',
    chronic_diseases: '',
    health_goals: ''
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  // Password Change Flow State
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [pwStep, setPwStep] = useState(1); // 1: QR/OTP, 2: New Password, 3: Success
  const [qrCode, setQrCode] = useState('');
  const [isOtpEnabled, setIsOtpEnabled] = useState(false);
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError] = useState('');
  const [showPw, setShowPw] = useState(false);

  useEffect(() => {
    loadProfile();
  }, []);

  const handleOpenPasswordModal = async () => {
    setPwLoading(true);
    setPwError('');
    try {
      const data = await securityService.initiateChangePassword();
      setQrCode(data.qr_code);
      setIsOtpEnabled(data.otp_enabled);
      setPwStep(1);
      setShowPasswordModal(true);
    } catch (error) {
      console.error("Failed to init password change:", error);
      setMessage('Failed to initiate password change. Please try again.');
    } finally {
      setPwLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (otp.length !== 6) {
      setPwError('Please enter a 6-digit OTP');
      return;
    }
    setPwLoading(true);
    setPwError('');
    try {
      await securityService.verifyOtp(otp);
      setPwStep(2);
    } catch (error) {
      setPwError(error.response?.data?.detail || 'Invalid OTP. Please try again.');
    } finally {
      setPwLoading(false);
    }
  };

  const handleCompletePasswordChange = async () => {
    if (newPassword !== confirmPassword) {
      setPwError('Passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      setPwError('Password must be at least 8 characters');
      return;
    }
    setPwLoading(true);
    setPwError('');
    try {
      await securityService.completeChangePassword(newPassword);
      setPwStep(3);
    } catch (error) {
      setPwError(error.response?.data?.detail || 'Failed to update password.');
    } finally {
      setPwLoading(false);
    }
  };

  const closePasswordModal = () => {
    setShowPasswordModal(false);
    setPwStep(1);
    setQrCode('');
    setOtp('');
    setNewPassword('');
    setConfirmPassword('');
    setPwError('');
  };

  const loadProfile = async () => {
    try {
      const data = await profileService.getProfile();
      if (data) {
        setProfile(prev => ({
          ...prev,
          ...data,
          age: data.age ?? '',
          weight_kg: data.weight_kg ?? '',
          height_cm: data.height_cm ?? '',
          allergies: data.allergies ?? '',
          chronic_diseases: data.chronic_diseases ?? '',
          health_goals: data.health_goals ?? '',
          gender: data.gender || 'Prefer not to say'
        }));
      }
    } catch (error) {
      console.error("Error loading profile:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setProfile(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage('');

    try {
      const payload = {
        ...profile,
        age: profile.age ? parseInt(profile.age) : null,
        weight_kg: profile.weight_kg ? parseFloat(profile.weight_kg) : null,
        height_cm: profile.height_cm ? parseFloat(profile.height_cm) : null,
      };

      await profileService.updateProfile(payload);
      setMessage('Profile updated successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error(error);
      setMessage('Failed to save profile. Please check your inputs.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-navy-950 flex flex-col items-center justify-center gap-4">
        <div className="w-12 h-12 border-4 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
        <span className="text-navy-300 font-medium animate-pulse">Accessing Secure Records...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white selection:bg-brand-100 selection:text-brand-900">
      <Header />
      
      {/* Decorative Background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-brand-50/50 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-navy-50/50 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
      </div>

      <main className="relative max-w-5xl mx-auto px-4 py-12 md:py-20">
        {/* Header Section */}
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2.5 bg-brand-600 rounded-2xl shadow-lg shadow-brand-600/20">
              <User className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-3xl font-extrabold text-navy-900 tracking-tight">Personal Health Profile</h1>
          </div>
          <p className="text-lg text-navy-500 max-w-2xl leading-relaxed">
            Personalize your AI health assistant for more accurate clinical insights and tailored health recommendations.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="grid lg:grid-cols-3 gap-8">
          {/* Left Column: Core Stats */}
          <div className="lg:col-span-2 space-y-8">
            <div className="bg-white rounded-[2.5rem] border border-navy-100 shadow-xl shadow-navy-900/5 p-8 md:p-10">
              <div className="flex items-center gap-3 mb-8">
                <div className="p-2 bg-navy-50 rounded-xl">
                  <Activity className="h-5 w-5 text-navy-600" />
                </div>
                <h2 className="text-xl font-bold text-navy-900">Biometric Information</h2>
              </div>

              <div className="grid sm:grid-cols-2 gap-x-10 gap-y-8">
                {/* Patient Name */}
                <div className="sm:col-span-2 space-y-2.5">
                  <label className="block text-xs font-bold text-navy-400 uppercase tracking-widest ml-1">Name</label>
                  <div className="relative group">
                    <input
                      type="text"
                      name="patient_name"
                      value={profile.patient_name}
                      onChange={handleChange}
                      className="w-full pl-12 pr-4 py-4 bg-navy-50/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all text-navy-900 font-semibold placeholder:text-navy-200"
                      placeholder="e.g. John Doe"
                    />
                    <User className="absolute left-4 top-4 h-5 w-5 text-navy-300 group-focus-within:text-brand-500 transition-colors" />
                  </div>
                </div>

                {/* Age */}
                <div className="space-y-2.5">
                  <label className="block text-xs font-bold text-navy-400 uppercase tracking-widest ml-1">Current Age</label>
                  <div className="relative group">
                    <input
                      type="number"
                      name="age"
                      value={profile.age}
                      onChange={handleChange}
                      className="w-full pl-12 pr-4 py-4 bg-navy-50/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all text-navy-900 font-semibold placeholder:text-navy-200"
                      placeholder="e.g. 25"
                    />
                    <Activity className="absolute left-4 top-4 h-5 w-5 text-navy-300 group-focus-within:text-brand-500 transition-colors" />
                  </div>
                </div>

                {/* Gender */}
                <div className="space-y-2.5">
                  <label className="block text-xs font-bold text-navy-400 uppercase tracking-widest ml-1">Gender Identity</label>
                  <div className="relative group">
                    <select
                      name="gender"
                      value={profile.gender}
                      onChange={handleChange}
                      className="w-full px-4 py-4 bg-navy-50/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all text-navy-900 font-semibold appearance-none cursor-pointer"
                    >
                      <option>Prefer not to say</option>
                      <option>Male</option>
                      <option>Female</option>
                      <option>Other</option>
                    </select>
                    <ChevronRight className="absolute right-4 top-4.5 h-5 w-5 text-navy-300 rotate-90 pointer-events-none" />
                  </div>
                </div>

                {/* Weight */}
                <div className="space-y-2.5">
                  <label className="block text-xs font-bold text-navy-400 uppercase tracking-widest ml-1">Weight (kg)</label>
                  <div className="relative group">
                    <input
                      type="number"
                      name="weight_kg"
                      value={profile.weight_kg}
                      onChange={handleChange}
                      className="w-full pl-12 pr-4 py-4 bg-navy-50/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all text-navy-900 font-semibold placeholder:text-navy-200"
                      placeholder="e.g. 70"
                    />
                    <Weight className="absolute left-4 top-4 h-5 w-5 text-navy-300 group-focus-within:text-brand-500 transition-colors" />
                  </div>
                </div>

                {/* Height */}
                <div className="space-y-2.5">
                  <label className="block text-xs font-bold text-navy-400 uppercase tracking-widest ml-1">Height (cm)</label>
                  <div className="relative group">
                    <input
                      type="number"
                      name="height_cm"
                      value={profile.height_cm}
                      onChange={handleChange}
                      className="w-full pl-12 pr-4 py-4 bg-navy-50/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all text-navy-900 font-semibold placeholder:text-navy-200"
                      placeholder="e.g. 175"
                    />
                    <Ruler className="absolute left-4 top-4 h-5 w-5 text-navy-300 group-focus-within:text-brand-500 transition-colors" />
                  </div>
                </div>
              </div>
            </div>

            {/* Medical Context */}
            <div className="bg-white rounded-[2.5rem] border border-navy-100 shadow-xl shadow-navy-900/5 p-8 md:p-10 space-y-8">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-navy-50 rounded-xl">
                  <ShieldCheck className="h-5 w-5 text-navy-600" />
                </div>
                <h2 className="text-xl font-bold text-navy-900">Clinical History & Context</h2>
              </div>

              <div className="space-y-6">
                <div className="space-y-2.5">
                  <label className="block text-xs font-bold text-navy-400 uppercase tracking-widest ml-1">Known Allergies</label>
                  <div className="relative group">
                    <textarea
                      name="allergies"
                      value={profile.allergies}
                      onChange={handleChange}
                      rows={3}
                      className="w-full pl-12 pr-4 py-4 bg-navy-50/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all text-navy-900 font-semibold placeholder:text-navy-200 resize-none"
                      placeholder="List any medication or environmental allergies..."
                    />
                    <AlertCircle className="absolute left-4 top-4.5 h-5 w-5 text-navy-300 group-focus-within:text-brand-500 transition-colors" />
                  </div>
                </div>

                <div className="space-y-2.5">
                  <label className="block text-xs font-bold text-navy-400 uppercase tracking-widest ml-1">Chronic Conditions</label>
                  <div className="relative group">
                    <textarea
                      name="chronic_diseases"
                      value={profile.chronic_diseases}
                      onChange={handleChange}
                      rows={3}
                      className="w-full pl-12 pr-4 py-4 bg-navy-50/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all text-navy-900 font-semibold placeholder:text-navy-200 resize-none"
                      placeholder="Existing diagnoses (e.g. Diabetes, Hypertension)..."
                    />
                    <Brain className="absolute left-4 top-4.5 h-5 w-5 text-navy-300 group-focus-within:text-brand-500 transition-colors" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Sidebar Actions */}
          <div className="space-y-8">
            {/* Health Goals Card */}
            <div className="bg-brand-600 rounded-[2.5rem] p-8 text-white shadow-xl shadow-brand-600/20">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                  <Heart className="h-5 w-5 text-white" />
                </div>
                <h2 className="text-xl font-bold">Health Goals</h2>
              </div>
              <textarea
                name="health_goals"
                value={profile.health_goals}
                onChange={handleChange}
                rows={4}
                className="w-full bg-white/10 border border-white/20 rounded-2xl p-4 text-white placeholder:text-white/50 focus:outline-none focus:ring-2 focus:ring-white/30 transition-all resize-none"
                placeholder="What are you working towards? (e.g. weight loss, stamina, sleep...)"
              />
              <p className="mt-4 text-xs text-brand-100/70 leading-relaxed italic">
                Defining your goals helps the AI tailor its wellness advice to your specific objectives.
              </p>
            </div>

            {/* Security & Actions */}
            <div className="bg-navy-900 rounded-[2.5rem] p-8 text-white shadow-xl shadow-navy-900/10">
              <div className="flex items-center gap-3 mb-8">
                <div className="p-2 bg-navy-800 rounded-xl">
                  <Lock className="h-5 w-5 text-brand-400" />
                </div>
                <h2 className="text-xl font-bold">Account Security</h2>
              </div>

              <div className="space-y-4">
                <button
                  type="button"
                  onClick={handleOpenPasswordModal}
                  className="w-full flex items-center justify-between p-4 bg-navy-800 hover:bg-navy-700 rounded-2xl transition-all group"
                >
                  <div className="flex items-center gap-3">
                    <KeyRound className="h-4 w-4 text-navy-400 group-hover:text-brand-400 transition-colors" />
                    <span className="text-sm font-semibold">Change Password</span>
                  </div>
                  <ChevronRight className="h-4 w-4 text-navy-500 group-hover:translate-x-1 transition-transform" />
                </button>

                <div className="p-4 bg-navy-800/50 rounded-2xl border border-navy-800">
                  <div className="flex gap-3">
                    <Info className="h-5 w-5 text-brand-400 shrink-0 mt-0.5" />
                    <p className="text-xs text-navy-300 leading-relaxed">
                      Your clinical data is encrypted and used only for providing personalized health assessments.
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-10 pt-8 border-t border-navy-800">
                <button
                  type="submit"
                  disabled={saving}
                  className={clsx(
                    "w-full py-4 rounded-2xl font-bold shadow-lg transition-all flex items-center justify-center gap-3 active:scale-[0.98]",
                    saving 
                      ? "bg-navy-700 text-navy-400 cursor-not-allowed" 
                      : "bg-brand-500 text-white hover:bg-brand-600 shadow-brand-500/20"
                  )}
                >
                  {saving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <span>Update Profile</span>
                      <Save className="h-5 w-5" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </form>

        {/* Floating Success Message */}
        {message && (
          <div className={clsx(
            "fixed bottom-8 left-1/2 -translate-x-1/2 px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-3 animate-in slide-in-from-bottom-10 duration-500 z-[100]",
            message.includes('success') ? "bg-teal-600 text-white" : "bg-red-600 text-white"
          )}>
            {message.includes('success') ? <ShieldCheck className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}
            <span className="font-bold text-sm">{message}</span>
          </div>
        )}
      </main>

      {/* Password Change Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-navy-950/60 backdrop-blur-md z-[200] flex items-center justify-center p-4">
          <div className="bg-white rounded-[2.5rem] shadow-2xl max-w-md w-full overflow-hidden animate-in fade-in zoom-in-95 duration-300">
            <div className="px-8 py-6 border-b border-navy-50 flex items-center justify-between bg-navy-50/30">
              <h3 className="font-bold text-navy-900 flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-brand-600" />
                Security Check
              </h3>
              <button onClick={closePasswordModal} className="p-2 hover:bg-navy-100 rounded-full transition-colors group">
                <X className="h-5 w-5 text-navy-400 group-hover:text-navy-600" />
              </button>
            </div>

            <div className="p-10">
              {pwStep === 1 && (
                <div className="space-y-8 text-center">
                  <div className="space-y-2">
                    <h4 className="text-xl font-bold text-navy-900">Step 1: Identity Check</h4>
                    <p className="text-sm text-navy-500 leading-relaxed">
                      {isOtpEnabled 
                        ? "Enter the 6-digit code from your authenticator app to verify your identity."
                        : "Scan this code with Microsoft Authenticator or any TOTP app to verify your identity."
                      }
                    </p>
                  </div>
                  
                  {!isOtpEnabled && qrCode && (
                    <div className="bg-white p-6 inline-block rounded-3xl border-2 border-navy-50 shadow-inner">
                      <img src={qrCode} alt="TOTP QR Code" className="w-48 h-48" />
                    </div>
                  )}

                  <div className="space-y-3 text-left">
                    <label className="block text-xs font-bold text-navy-400 uppercase tracking-widest ml-1">6-Digit Verification Code</label>
                    <input
                      type="text"
                      maxLength={6}
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                      className="w-full px-4 py-5 text-center text-3xl tracking-[0.4em] font-mono bg-navy-50/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all text-navy-900 font-bold placeholder:text-navy-200"
                      placeholder="000000"
                    />
                    {pwError && <p className="text-xs text-red-600 font-medium flex items-center gap-1.5"><AlertCircle className="h-3.5 w-3.5" /> {pwError}</p>}
                  </div>

                  <button
                    onClick={handleVerifyOtp}
                    disabled={pwLoading || otp.length !== 6}
                    className="w-full bg-brand-600 text-white py-4 rounded-2xl font-bold shadow-lg shadow-brand-600/20 hover:bg-brand-700 transition-all disabled:opacity-50 active:scale-[0.98]"
                  >
                    {pwLoading ? 'Verifying Identity...' : 'Verify & Continue'}
                  </button>
                </div>
              )}

              {pwStep === 2 && (
                <div className="space-y-8">
                  <div className="space-y-2 text-center">
                    <h4 className="text-xl font-bold text-navy-900">Step 2: Update Credentials</h4>
                    <p className="text-sm text-navy-500">Your identity is verified. Please enter a strong new password.</p>
                  </div>

                  <div className="space-y-5">
                    <div className="space-y-2.5">
                      <label className="block text-xs font-bold text-navy-400 uppercase tracking-widest ml-1">New Secure Password</label>
                      <div className="relative group">
                        <input
                          type={showPw ? "text" : "password"}
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          className="w-full pl-12 pr-12 py-4 bg-navy-50/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all text-navy-900 font-semibold placeholder:text-navy-200"
                          placeholder="••••••••"
                        />
                        <KeyRound className="absolute left-4 top-4 h-5 w-5 text-navy-300 group-focus-within:text-brand-500 transition-colors" />
                        <button 
                          type="button"
                          onClick={() => setShowPw(!showPw)}
                          className="absolute right-4 top-4 text-navy-300 hover:text-navy-600 transition-colors"
                        >
                          {showPw ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                        </button>
                      </div>
                    </div>

                    <div className="space-y-2.5">
                      <label className="block text-xs font-bold text-navy-400 uppercase tracking-widest ml-1">Confirm New Password</label>
                      <div className="relative group">
                        <input
                          type={showPw ? "text" : "password"}
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          className="w-full pl-12 pr-4 py-4 bg-navy-50/50 border-2 border-transparent rounded-2xl focus:bg-white focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all text-navy-900 font-semibold placeholder:text-navy-200"
                          placeholder="••••••••"
                        />
                        <KeyRound className="absolute left-4 top-4 h-5 w-5 text-navy-300 group-focus-within:text-brand-500 transition-colors" />
                      </div>
                    </div>

                    {pwError && <p className="text-xs text-red-600 font-medium flex items-center gap-1.5"><AlertCircle className="h-3.5 w-3.5" /> {pwError}</p>}
                  </div>

                  <button
                    onClick={handleCompletePasswordChange}
                    disabled={pwLoading}
                    className="w-full bg-brand-600 text-white py-4 rounded-2xl font-bold shadow-lg shadow-brand-600/20 hover:bg-brand-700 transition-all disabled:opacity-50 active:scale-[0.98]"
                  >
                    {pwLoading ? 'Updating Secure Vault...' : 'Confirm Update'}
                  </button>
                </div>
              )}

              {pwStep === 3 && (
                <div className="space-y-8 text-center">
                  <div className="w-24 h-24 bg-teal-50 rounded-full flex items-center justify-center mx-auto shadow-inner">
                    <ShieldCheck className="h-12 w-12 text-teal-600" />
                  </div>
                  <div className="space-y-3">
                    <h4 className="text-2xl font-extrabold text-navy-900">Account Secured</h4>
                    <p className="text-navy-500 leading-relaxed">Your password has been updated securely. Please use your new credentials for future sessions.</p>
                  </div>
                  <button
                    onClick={closePasswordModal}
                    className="w-full bg-navy-900 text-white py-4 rounded-2xl font-bold hover:bg-navy-800 transition-all active:scale-[0.98] shadow-xl shadow-navy-900/10"
                  >
                    Return to Profile
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;
