import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/api';
import { Activity, ArrowRight, Loader2, Mail, CheckCircle, Lock, ShieldCheck, HeartPulse } from 'lucide-react';

const Login = () => {
  const [view, setView] = useState('login'); // 'login', 'signup', 'forgot'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      if (view === 'login') {
        const data = await authService.login(email, password);
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('email', data.email);
        navigate('/chat');
      } else if (view === 'signup') {
        const data = await authService.signup(email, password);
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('email', data.email);
        navigate('/chat');
      } else if (view === 'forgot') {
        await authService.forgotPassword(email);
        setSuccessMessage('If the account exists, a reset email has been sent.');
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Action failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getTitle = () => {
    if (view === 'login') return 'Welcome Back';
    if (view === 'signup') return 'Create Account';
    return 'Forgot Password';
  };

  const getSubtitle = () => {
    if (view === 'login') return 'Access your personal health assistant';
    if (view === 'signup') return 'Start your journey to better health';
    return 'We will send you a link to reset your password';
  };

  const getIcon = () => {
    if (view === 'forgot') return <Mail className="h-7 w-7 text-white" />;
    if (view === 'signup') return <ShieldCheck className="h-7 w-7 text-white" />;
    return <Activity className="h-7 w-7 text-white" />;
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-brand-50 via-white to-navy-50 flex items-center justify-center p-6 font-sans">
      <div className="w-full max-w-5xl grid lg:grid-cols-2 bg-white rounded-3xl shadow-premium overflow-hidden border border-navy-100 animate-fade-in">
        
        {/* Left Side: Aesthetic Branding */}
        <div className="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-navy-900 to-navy-800 text-white relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-brand-500/10 rounded-full -mr-32 -mt-32 blur-3xl"></div>
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-teal-500/10 rounded-full -ml-32 -mb-32 blur-3xl"></div>
          
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-12">
              <div className="p-2 bg-brand-500 rounded-lg shadow-lg shadow-brand-500/30">
                <HeartPulse className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight">HealthGuide AI</span>
            </div>
            
            <h1 className="text-4xl font-extrabold leading-tight mb-6">
              Your intelligent <br />
              <span className="text-brand-400">Health Companion.</span>
            </h1>
            <p className="text-navy-300 text-lg max-w-sm leading-relaxed">
              Experience the next generation of healthcare with AI-driven insights and personalized monitoring.
            </p>
          </div>

          <div className="relative z-10 grid grid-cols-2 gap-6">
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <div className="text-2xl font-bold text-brand-400">24/7</div>
              <div className="text-sm text-navy-300">Active Monitoring</div>
            </div>
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <div className="text-2xl font-bold text-teal-400">99%</div>
              <div className="text-sm text-navy-300">Accuracy Rate</div>
            </div>
          </div>
        </div>

        {/* Right Side: Form */}
        <div className="p-8 lg:p-16 flex flex-col justify-center relative">
          <div className="max-w-sm mx-auto w-full animate-slide-up">
            <div className="mb-10 text-center lg:text-left">
              <div className="lg:hidden mx-auto w-14 h-14 bg-brand-600 rounded-2xl flex items-center justify-center mb-6 shadow-xl shadow-brand-600/20">
                {getIcon()}
              </div>
              <h2 className="text-3xl font-bold text-navy-900 tracking-tight mb-2">
                {getTitle()}
              </h2>
              <p className="text-navy-500">
                {getSubtitle()}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="p-4 bg-red-50 border border-red-100 text-red-600 text-sm rounded-xl flex items-center gap-3 animate-pulse-soft">
                  <div className="h-1.5 w-1.5 rounded-full bg-red-600"></div>
                  {error}
                </div>
              )}

              {successMessage && (
                <div className="p-4 bg-teal-50 border border-teal-100 text-teal-700 text-sm rounded-xl flex items-center gap-3">
                  <CheckCircle className="h-5 w-5 text-teal-600" />
                  {successMessage}
                </div>
              )}
              
              <div className="space-y-2">
                <label className="text-sm font-semibold text-navy-700 ml-1">Email Address</label>
                <div className="relative group">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-navy-400 group-focus-within:text-brand-600 transition-colors" />
                  <input
                    type="email"
                    required
                    className="w-full pl-12 pr-4 py-3.5 bg-navy-50/50 border border-navy-100 rounded-xl focus:ring-4 focus:ring-brand-500/10 focus:border-brand-500 focus:bg-white transition-all outline-none text-navy-900 placeholder:text-navy-300"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                  />
                </div>
              </div>
              
              {view !== 'forgot' && (
                <div className="space-y-2">
                  <div className="flex justify-between items-center ml-1">
                    <label className="text-sm font-semibold text-navy-700">Password</label>
                    {view === 'login' && (
                      <button
                        type="button"
                        onClick={() => {
                          setView('forgot');
                          setError('');
                          setSuccessMessage('');
                        }}
                        className="text-xs text-brand-600 hover:text-brand-700 font-bold transition-colors"
                      >
                        Forgot Password?
                      </button>
                    )}
                  </div>
                  <div className="relative group">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-navy-400 group-focus-within:text-brand-600 transition-colors" />
                    <input
                      type="password"
                      required
                      className="w-full pl-12 pr-4 py-3.5 bg-navy-50/50 border border-navy-100 rounded-xl focus:ring-4 focus:ring-brand-500/10 focus:border-brand-500 focus:bg-white transition-all outline-none text-navy-900 placeholder:text-navy-300"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                    />
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-navy-900 text-white py-4 rounded-xl font-bold hover:bg-navy-800 active:scale-[0.98] transition-all flex items-center justify-center gap-3 shadow-xl shadow-navy-900/10 group disabled:opacity-70 disabled:pointer-events-none"
              >
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    <span className="text-lg">
                      {view === 'login' ? 'Sign In' : view === 'signup' ? 'Create Account' : 'Reset Password'}
                    </span>
                    <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </button>
            </form>

            <div className="mt-10 pt-8 border-t border-navy-50 text-center">
              {view === 'forgot' ? (
                <button
                  onClick={() => {
                    setView('login');
                    setError('');
                    setSuccessMessage('');
                  }}
                  className="text-sm text-navy-500 hover:text-brand-600 font-semibold transition-colors"
                >
                  Return to <span className="text-brand-600">Sign In</span>
                </button>
              ) : (
                <button
                  onClick={() => {
                    setView(view === 'login' ? 'signup' : 'login');
                    setError('');
                    setSuccessMessage('');
                  }}
                  className="text-sm text-navy-500 font-medium transition-colors"
                >
                  {view === 'login' ? (
                    <>New here? <span className="text-brand-600 font-bold ml-1">Create an account</span></>
                  ) : (
                    <>Already have an account? <span className="text-brand-600 font-bold ml-1">Sign in instead</span></>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
