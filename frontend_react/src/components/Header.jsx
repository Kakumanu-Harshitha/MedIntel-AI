import React, { useState, useEffect } from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { LogOut, User, HeartPulse, Menu, X, FileText, MessageSquare, ShieldCheck, ChevronRight } from 'lucide-react';
import { authService, profileService } from '../services/api';
import clsx from 'clsx';

const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [profileWarning, setProfileWarning] = useState(false);
  const email = localStorage.getItem('email');
  const isLoggedIn = !!email;
  const username = email ? email.split('@')[0] : '';

  useEffect(() => {
    if (isLoggedIn) {
      profileService.getProfile()
        .then(data => {
          if (!data.age || !data.height_cm || !data.weight_kg) {
            setProfileWarning(true);
          } else {
            setProfileWarning(false);
          }
        })
        .catch(err => console.error("Profile check failed", err));
    }
  }, [isLoggedIn, location.pathname]);

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
    setIsMenuOpen(false);
  };

  const navItems = [
    { name: 'Assessment', path: '/assessment', icon: MessageSquare },
    { name: 'Reports', path: '/reports', icon: FileText },
    { name: 'Profile', path: '/profile', icon: User, warning: profileWarning },
  ];

  return (
    <header className="border-b border-navy-100 bg-white/70 backdrop-blur-xl sticky top-0 z-50 font-sans">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 group transition-transform active:scale-95" onClick={() => setIsMenuOpen(false)}>
          <div className="bg-brand-600 p-2.5 rounded-2xl shadow-lg shadow-brand-600/20 group-hover:rotate-3 transition-transform">
            <HeartPulse className="h-6 w-6 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="font-extrabold text-xl text-navy-900 tracking-tight leading-none">HealthGuide</span>
            <span className="text-[10px] font-bold text-brand-600 tracking-[0.2em] uppercase mt-0.5">Assistant AI</span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        {isLoggedIn && (
          <nav className="hidden md:flex items-center gap-2 bg-navy-50/50 p-1.5 rounded-2xl border border-navy-100">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => clsx(
                  "px-6 py-2.5 rounded-xl text-sm font-bold transition-all flex items-center gap-2 relative group",
                  isActive 
                    ? "bg-white text-brand-600 shadow-premium" 
                    : "text-navy-500 hover:text-navy-900"
                )}
              >
                <item.icon className={clsx("h-4 w-4 transition-transform group-hover:scale-110")} />
                {item.name}
                {item.warning && (
                  <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white animate-pulse" />
                )}
              </NavLink>
            ))}
          </nav>
        )}

        {/* Right Actions */}
        <div className="hidden md:flex items-center gap-6">
          {isLoggedIn ? (
            <div className="flex items-center gap-5">
              <div className="flex flex-col items-end">
                <span className="text-xs font-bold text-navy-400 uppercase tracking-wider">Patient</span>
                <span className="text-sm font-bold text-navy-900">{username}</span>
              </div>
              <div className="h-10 w-px bg-navy-100" />
              <button 
                onClick={handleLogout}
                className="p-2.5 rounded-2xl text-navy-400 hover:text-red-600 hover:bg-red-50 transition-all border border-transparent hover:border-red-100"
                title="Sign Out"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <Link to="/login" className="text-sm font-bold text-navy-600 hover:text-brand-600 transition-colors px-4">
                Log in
              </Link>
              <Link 
                to="/login" 
                className="bg-navy-900 text-white px-7 py-3 rounded-2xl text-sm font-bold hover:bg-navy-800 transition-all shadow-xl shadow-navy-900/10 active:scale-95"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>

        {/* Mobile Menu Button */}
        <button 
          className="md:hidden p-3 text-navy-600 hover:bg-navy-50 rounded-2xl transition-colors"
          onClick={() => setIsMenuOpen(!isMenuOpen)}
        >
          {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isMenuOpen && (
        <div className="md:hidden bg-white border-t border-navy-50 absolute w-full left-0 top-20 shadow-2xl py-6 px-6 flex flex-col gap-4 animate-fade-in z-50">
          {isLoggedIn ? (
            <>
              <div className="flex items-center gap-4 p-4 bg-navy-50 rounded-2xl mb-2">
                <div className="h-12 w-12 rounded-full bg-brand-100 flex items-center justify-center text-brand-600 font-bold text-lg">
                  {username[0].toUpperCase()}
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-navy-400 uppercase tracking-wider">Signed in as</span>
                  <span className="text-base font-bold text-navy-900">{username}</span>
                </div>
              </div>
              
              <div className="space-y-2">
                {navItems.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => setIsMenuOpen(false)}
                    className={({ isActive }) => clsx(
                      "px-5 py-4 rounded-2xl text-base font-bold transition-all flex items-center justify-between group",
                      isActive 
                        ? "bg-brand-50 text-brand-600" 
                        : "text-navy-600 hover:bg-navy-50"
                    )}
                  >
                    <div className="flex items-center gap-4">
                      <item.icon className="h-5 w-5" />
                      {item.name}
                    </div>
                    {item.warning ? (
                      <ShieldCheck className="h-5 w-5 text-red-500 animate-pulse" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-navy-300 group-hover:translate-x-1 transition-transform" />
                    )}
                  </NavLink>
                ))}
              </div>

              <div className="h-px bg-navy-50 my-2" />
              
              <button 
                onClick={handleLogout}
                className="w-full px-5 py-4 rounded-2xl text-base font-bold text-red-600 hover:bg-red-50 transition-all flex items-center gap-4"
              >
                <LogOut className="h-5 w-5" />
                Sign Out
              </button>
            </>
          ) : (
            <div className="flex flex-col gap-4">
              <Link 
                to="/login" 
                onClick={() => setIsMenuOpen(false)}
                className="w-full py-4 text-center rounded-2xl font-bold text-navy-600 hover:bg-navy-50 border border-navy-100"
              >
                Log in
              </Link>
              <Link 
                to="/login" 
                onClick={() => setIsMenuOpen(false)}
                className="w-full py-4 text-center rounded-2xl font-bold bg-navy-900 text-white shadow-xl shadow-navy-900/10"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
};

export default Header;
