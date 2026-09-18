import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { PaymentModal } from './PaymentModal';
import { CheckoutResponse } from '../services/paymentService';
import {
  Layers,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  SlidersHorizontal,
  FileText,
  ShieldCheck,
  Zap,
  Scan,
  Compass,
  Cpu,
  Building2,
  Wrench,
  ChevronRight,
  ExternalLink,
  Lock,
  FileCode,
  Eye,
  Check,
  X,
  Play,
  CreditCard,
  Smartphone,
  Receipt,
  HelpCircle,
} from 'lucide-react';


interface LandingPageProps {
  onLaunchApp: () => void;
  onOpenAuthModal?: (tab?: 'login' | 'register') => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onLaunchApp,
  onOpenAuthModal,
}) => {
  const { isAuthenticated } = useAuth();
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');
  const [isSignInModalOpen, setIsSignInModalOpen] = useState(false);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [selectedPaymentPlan, setSelectedPaymentPlan] = useState<'starter' | 'pro' | 'enterprise'>('pro');
  const [paymentSuccessNotice, setPaymentSuccessNotice] = useState<string | null>(null);
  const [demoActiveTab, setDemoActiveTab] = useState<'split' | 'curtain' | 'delta'>('split');
  const [emailInput, setEmailInput] = useState('');
  const [signedInNotice, setSignedInNotice] = useState(false);

  const handleOpenPayment = (plan: 'starter' | 'pro' | 'enterprise') => {
    setSelectedPaymentPlan(plan);
    setIsPaymentModalOpen(true);
  };

  const handlePaymentSuccess = (res: CheckoutResponse) => {
    setPaymentSuccessNotice(`Payment successful! ${res.plan_name} active (${res.transaction_id}).`);
    setTimeout(() => {
      setPaymentSuccessNotice(null);
    }, 6000);
  };

  const handleSignInSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSignedInNotice(true);
    setTimeout(() => {
      setIsSignInModalOpen(false);
      setSignedInNotice(false);
      onLaunchApp();
    }, 1200);
  };

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-[#0A0A0A] font-sans antialiased flex flex-col selection:bg-[#0A0A0A] selection:text-white">
      {/* 1. Floating Navigation Bar */}
      <header
        id="landing-navbar"
        className="sticky top-3 sm:top-4 z-50 px-3 sm:px-6"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-5 h-14 flex items-center justify-between bg-white/95 backdrop-blur-md rounded-[14px] border border-[#E5E5E5]/80 shadow-[0_10px_36px_-16px_rgba(0,0,0,0.22)]">
          {/* Logo */}
          <div
            onClick={onLaunchApp}
            className="flex items-center gap-2.5 cursor-pointer select-none group"
          >
            <div className="w-8 h-8 bg-[#0A0A0A] group-hover:bg-[#171717] rounded-[10px] flex items-center justify-center text-white font-bold text-[13px] shrink-0 shadow-xs transition-colors">
              Δ
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#737373] leading-none">
                Engineering Review
              </span>
              <span className="text-[15px] font-extrabold tracking-tight text-[#0A0A0A] leading-tight">
                Drawing Diff AI
              </span>
            </div>
          </div>

          {/* Center Links */}
          <nav className="hidden md:flex items-center gap-7 text-[13px] font-semibold text-[#525252]">
            <button
              onClick={() => scrollToSection('features-section')}
              className="relative py-1 hover:text-[#0A0A0A] transition-colors cursor-pointer after:absolute after:left-0 after:-bottom-0.5 after:h-[2px] after:w-0 after:rounded-full after:bg-[#0A0A0A] hover:after:w-full after:transition-all after:duration-200"
            >
              Features
            </button>
            <button
              onClick={() => scrollToSection('how-it-works-section')}
              className="relative py-1 hover:text-[#0A0A0A] transition-colors cursor-pointer after:absolute after:left-0 after:-bottom-0.5 after:h-[2px] after:w-0 after:rounded-full after:bg-[#0A0A0A] hover:after:w-full after:transition-all after:duration-200"
            >
              How it Works
            </button>
            <button
              onClick={() => scrollToSection('industries-section')}
              className="relative py-1 hover:text-[#0A0A0A] transition-colors cursor-pointer after:absolute after:left-0 after:-bottom-0.5 after:h-[2px] after:w-0 after:rounded-full after:bg-[#0A0A0A] hover:after:w-full after:transition-all after:duration-200"
            >
              Industries
            </button>
            <button
              onClick={() => scrollToSection('pricing-section')}
              className="relative py-1 hover:text-[#0A0A0A] transition-colors cursor-pointer after:absolute after:left-0 after:-bottom-0.5 after:h-[2px] after:w-0 after:rounded-full after:bg-[#0A0A0A] hover:after:w-full after:transition-all after:duration-200"
            >
              Pricing
            </button>
            <button
              onClick={() => scrollToSection('docs-section')}
              className="relative py-1 hover:text-[#0A0A0A] transition-colors cursor-pointer after:absolute after:left-0 after:-bottom-0.5 after:h-[2px] after:w-0 after:rounded-full after:bg-[#0A0A0A] hover:after:w-full after:transition-all after:duration-200 flex items-center gap-1"
            >
              <span>Docs</span>
              <ExternalLink className="w-3 h-3 text-[#A3A3A3]" />
            </button>
          </nav>

          {/* Right Actions */}
          <div className="flex items-center gap-3 sm:gap-4">
            <button
              id="btn-nav-get-started"
              onClick={() => {
                if (isAuthenticated) {
                  onLaunchApp();
                } else if (onOpenAuthModal) {
                  onOpenAuthModal('login');
                } else {
                  onLaunchApp();
                }
              }}
              className="group inline-flex items-center gap-2 px-5 py-2 bg-[#0A0A0A] hover:bg-[#262626] text-[#FFFFFF] text-[13px] font-semibold rounded-[9999px] transition-all duration-200 cursor-pointer shadow-xs active:scale-[0.98]"
            >
              <span>{isAuthenticated ? 'New Comparison' : 'Get Started'}</span>
              <ArrowRight className="w-3.5 h-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
            </button>
          </div>
        </div>
      </header>

      {/* 2. Hero Section (Split Layout: 45/55) */}
      <section
        id="hero-section"
        className="w-full max-w-7xl mx-auto px-4 sm:px-6 pt-12 pb-16 sm:py-20 lg:py-24"
      >
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
          {/* Left Column (Text Content) */}
          <div className="lg:col-span-5 flex flex-col items-start text-left space-y-5">
            {/* Eyebrow badge */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-[8px] bg-white border border-[#E5E5E5] text-xs text-[#0A0A0A] shadow-2xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-semibold uppercase tracking-wider text-[11px]">
                AI-Powered CAD & Drawing Comparison
              </span>
            </div>

            {/* Main Headline */}
            <h1 className="text-[34px] sm:text-[42px] lg:text-[44px] font-bold text-[#0A0A0A] tracking-tight leading-[1.12]">
              Catch every drawing revision change, automatically.
            </h1>

            {/* Subheadline */}
            <p className="text-[15px] sm:text-[16px] text-[#525252] leading-relaxed">
              Instantly detect dimensional shifts, modified tolerances, geometric delta regions,
              and deleted notes across CAD drawings and engineering schematics in seconds.
            </p>

            {/* Primary & Secondary CTAs */}
            <div className="pt-2 flex flex-wrap items-center gap-4 w-full sm:w-auto">
              <button
                id="btn-hero-cta"
                onClick={onLaunchApp}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-7 py-3.5 bg-[#0A0A0A] hover:bg-[#171717] text-white text-[14px] font-semibold rounded-[9999px] transition-all cursor-pointer shadow-md hover:shadow-lg active:scale-[0.98]"
              >
                <span>Try Free Comparison</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                id="btn-hero-pricing"
                onClick={() => scrollToSection('pricing-section')}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-white border border-[#E5E5E5] hover:border-[#0A0A0A] text-[#0A0A0A] text-[14px] font-semibold rounded-[9999px] transition-colors cursor-pointer group shadow-xs"
              >
                <CreditCard className="w-4 h-4 text-blue-600" />
                <span>View Pricing & Payment</span>
              </button>
            </div>

            {/* Small Trust Line */}
            <div className="pt-2 flex items-center gap-2 text-[12px] text-[#737373] font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>No credit card required • ISO 10209 & ASME Y14.5 compliant</span>
            </div>
          </div>

          {/* Right Column (Product Browser Frame Mockup) */}
          <div className="lg:col-span-7 relative p-2 sm:p-4">
            <div className="bg-white border border-[#E5E5E5] rounded-[12px] shadow-xl overflow-hidden flex flex-col my-3 mx-1">
              <div className="px-4 py-3 bg-[#FAFAFA] border-b border-[#E5E5E5] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-[#E5E5E5]" />
                  <div className="w-2.5 h-2.5 rounded-full bg-[#E5E5E5]" />
                  <div className="w-2.5 h-2.5 rounded-full bg-[#E5E5E5]" />
                  <span className="ml-2 text-[11px] text-[#737373] font-medium">
                    FLG-204 · Mechanical Flange (Rev A vs Rev B)
                  </span>
                </div>

                <div className="flex bg-[#E5E5E5] p-[2px] rounded-[9999px] text-[10px] font-semibold">
                  <button
                    onClick={() => setDemoActiveTab('split')}
                    className={`px-2 py-0.5 rounded-[9999px] transition-all cursor-pointer ${
                      demoActiveTab === 'split' ? 'bg-white text-[#0A0A0A] font-bold shadow-2xs' : 'text-[#525252]'
                    }`}
                  >
                    Split
                  </button>
                  <button
                    onClick={() => setDemoActiveTab('curtain')}
                    className={`px-2 py-0.5 rounded-[9999px] transition-all cursor-pointer ${
                      demoActiveTab === 'curtain' ? 'bg-white text-[#0A0A0A] font-bold shadow-2xs' : 'text-[#525252]'
                    }`}
                  >
                    Curtain
                  </button>
                  <button
                    onClick={() => setDemoActiveTab('delta')}
                    className={`px-2 py-0.5 rounded-[9999px] transition-all cursor-pointer ${
                      demoActiveTab === 'delta' ? 'bg-white text-[#0A0A0A] font-bold shadow-2xs' : 'text-[#525252]'
                    }`}
                  >
                    Delta Grid
                  </button>
                </div>
              </div>

              <div className="relative bg-[#FAFAFA] p-4 sm:p-5 h-[340px] sm:h-[370px] flex items-center justify-center">
                <div className="w-full h-full border border-[#E5E5E5] rounded-[8px] bg-white p-3.5 flex flex-col justify-between relative shadow-2xs">
                  <svg className="w-full h-[220px] sm:h-[240px] text-[#E5E5E5]" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <pattern id="grid-pattern-hero" width="24" height="24" patternUnits="userSpaceOnUse">
                        <path d="M 24 0 L 0 0 0 24" fill="none" stroke="currentColor" strokeWidth="0.5" />
                      </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#grid-pattern-hero)" />

                    <circle cx="35%" cy="50%" r="55" fill="none" stroke="#0A0A0A" strokeWidth="1.8" />
                    <circle cx="35%" cy="50%" r="30" fill="none" stroke="#0A0A0A" strokeWidth="1.2" strokeDasharray="3 3" />
                    <circle cx="35%" cy="18" r="18" fill="none" stroke="#0A0A0A" strokeWidth="1.5" />
                    <circle cx="35%" cy="28%" r="4" fill="none" stroke="#0A0A0A" strokeWidth="1.2" />
                    <circle cx="35%" cy="72%" r="4" fill="none" stroke="#0A0A0A" strokeWidth="1.2" />
                    <circle cx="21%" cy="50%" r="4" fill="none" stroke="#0A0A0A" strokeWidth="1.2" />
                    <circle cx="49%" cy="50%" r="4" fill="none" stroke="#0A0A0A" strokeWidth="1.2" />

                    <circle cx="75%" cy="50%" r="55" fill="none" stroke="#0A0A0A" strokeWidth="1.8" />
                    <circle cx="75%" cy="50%" r="32" fill="none" stroke="#D97706" strokeWidth="1.8" strokeDasharray="4 2" />
                    <circle cx="75%" cy="50%" r="20" fill="none" stroke="#D97706" strokeWidth="1.8" />
                    <circle cx="75%" cy="26%" r="4.5" fill="#FEF3C7" stroke="#D97706" strokeWidth="1.5" />
                    <circle cx="75%" cy="74%" r="4.5" fill="#FEF3C7" stroke="#D97706" strokeWidth="1.5" />
                    <circle cx="61%" cy="38%" r="4.5" fill="#FEF3C7" stroke="#D97706" strokeWidth="1.5" />
                    <circle cx="89%" cy="38%" r="4.5" fill="#FEF3C7" stroke="#D97706" strokeWidth="1.5" />
                    <circle cx="61%" cy="62%" r="4.5" fill="#FEF3C7" stroke="#D97706" strokeWidth="1.5" />
                    <circle cx="89%" cy="62%" r="4.5" fill="#FEF3C7" stroke="#D97706" strokeWidth="1.5" />

                    <line x1="55%" y1="0" x2="55%" y2="100%" stroke="#E5E5E5" strokeWidth="2" strokeDasharray="4 4" />
                  </svg>

                  <div className="absolute top-[22%] right-[16%] w-24 h-16 border-2 border-amber-500 bg-amber-500/10 rounded-[6px] animate-pulse pointer-events-none flex items-start justify-end p-1">
                    <span className="text-[9px] font-semibold font-mono text-amber-700 bg-white px-1 rounded shadow-2xs">
                      Δ CHG-01
                    </span>
                  </div>

                  <div className="mt-2 pt-2 border-t border-[#E5E5E5] flex items-center justify-between text-[11px] text-[#525252]">
                    <span className="font-bold text-[#0A0A0A]">Rev A (4-Bolt) → Rev B (6-Bolt M8)</span>
                    <span className="text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded-[6px] border border-emerald-200">
                      Sub-pixel Match 99.4%
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="absolute top-0 left-4 sm:-left-1 bg-white border border-[#E5E5E5] rounded-[10px] p-3 shadow-xl flex items-center gap-2.5 z-20">
              <div className="w-8 h-8 rounded-[8px] bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-700 font-bold text-xs">
                Δ
              </div>
              <div className="flex flex-col">
                <span className="text-[12px] font-bold text-[#0A0A0A]">
                  4 Changes Detected
                </span>
                <span className="text-[10px] text-[#525252]">
                  2 Dimensions · 1 Note · 1 Hole
                </span>
              </div>
            </div>

            <div className="absolute bottom-0 right-4 sm:-right-1 bg-[#0A0A0A] text-white rounded-[10px] p-3 shadow-xl flex items-center gap-3 z-20">
              <div className="w-7 h-7 rounded-[6px] bg-neutral-800 flex items-center justify-center text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div className="flex flex-col">
                <span className="text-[11px] font-bold tracking-tight text-white">
                  ECO REPORT GENERATED
                </span>
                <span className="text-[10px] text-[#A3A3A3]">
                  ISO 10209 Verified • PDF/JSON
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Problem & Solution Contrast Section */}
      <section className="w-full bg-[#FAFAFA] border-y border-[#E5E5E5] py-16 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-[28px] sm:text-[34px] font-bold text-[#0A0A0A] tracking-tight">
              Manual drawing review is slow and error-prone.
            </h2>
            <p className="text-[15px] text-[#525252] mt-3 leading-relaxed">
              Engineering teams spend critical design cycles overlaying revisions and redlining sheets.
              Drawing Diff AI flags every geometric and dimensional shift instantly.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between space-y-4 shadow-xs">
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-6 h-6 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 font-bold text-xs">
                    ✕
                  </div>
                  <span className="text-xs font-bold text-rose-700 uppercase tracking-wider">
                    Traditional Manual Review
                  </span>
                </div>
                <h3 className="text-[18px] font-semibold text-[#0A0A0A] mb-3">
                  Tedious pixel-hunting & missed discrepancies
                </h3>
                <ul className="space-y-2.5 text-[14px] text-[#525252]">
                  <li className="flex items-start gap-2">
                    <span className="text-rose-500 shrink-0 font-bold">•</span>
                    <span>Subtle 0.2mm tolerance changes frequently slip past visual review</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-rose-500 shrink-0 font-bold">•</span>
                    <span>Manual entry of change orders into spreadsheets consumes engineering bandwidth</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-rose-500 shrink-0 font-bold">•</span>
                    <span>Scanned or rotated sheets require tedious manual coordinate alignment</span>
                  </li>
                </ul>
              </div>
              <div className="pt-3 border-t border-[#E5E5E5] text-[12px] text-[#A3A3A3]">
                Typical turnaround: 45 – 90 minutes per sheet
              </div>
            </div>

            <div className="bg-[#0A0A0A] text-white rounded-[12px] p-6 flex flex-col justify-between space-y-4 shadow-md">
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">
                    ✓
                  </div>
                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                    Drawing Diff AI Automation
                  </span>
                </div>
                <h3 className="text-[18px] font-semibold text-white mb-3">
                  Sub-pixel alignment and structured ISO reports in seconds
                </h3>
                <ul className="space-y-2.5 text-[14px] text-[#D4D4D4]">
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-400 shrink-0 font-bold">•</span>
                    <span>Automatic affine registration handles scale, rotation & scan skew</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-400 shrink-0 font-bold">•</span>
                    <span>Categorized delta table (dimensions, GD&T, notes, geometry)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-400 shrink-0 font-bold">•</span>
                    <span>One-click formal Engineering Change Order (ECO) PDF & JSON export</span>
                  </li>
                </ul>
              </div>
              <div className="pt-3 border-t border-neutral-800 text-[12px] text-[#A3A3A3]">
                Automated turnaround: &lt; 3 seconds (99.4% sub-pixel accuracy)
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Features Grid */}
      <section
        id="features-section"
        className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-24"
      >
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-[8px] bg-white border border-[#E5E5E5] text-xs text-[#525252] mb-3 font-medium">
            <Zap className="w-3.5 h-3.5 text-[#0A0A0A]" />
            <span className="font-bold uppercase tracking-wider text-[11px]">Precision Engine</span>
          </div>
          <h2 className="text-[28px] sm:text-[36px] font-bold text-[#0A0A0A] tracking-tight">
            Engineered for high-tolerance revision verification
          </h2>
          <p className="text-[15px] text-[#525252] mt-3 leading-relaxed">
            Every feature is calibrated to the strict standards of aerospace, mechanical, AEC,
            and PCB manufacturing pipelines.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between hover:border-[#A3A3A3] transition-all shadow-xs group">
            <div>
              <div className="w-10 h-10 rounded-[8px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] group-hover:bg-[#0A0A0A] group-hover:text-white transition-colors mb-4">
                <Scan className="w-5 h-5" />
              </div>
              <h3 className="text-[18px] font-semibold text-[#0A0A0A] mb-2">
                Automatic Alignment
              </h3>
              <p className="text-[14px] text-[#525252] leading-relaxed">
                Handles rotation, scale differentials, scan skew, and crop shifts with sub-pixel coordinate registration.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-[#E5E5E5] text-[11px] text-[#A3A3A3]">
              Affine & Feature Homography
            </div>
          </div>

          <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between hover:border-[#A3A3A3] transition-all shadow-xs group">
            <div>
              <div className="w-10 h-10 rounded-[8px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] group-hover:bg-[#0A0A0A] group-hover:text-white transition-colors mb-4">
                <SlidersHorizontal className="w-5 h-5" />
              </div>
              <h3 className="text-[18px] font-semibold text-[#0A0A0A] mb-2">
                Dimension & Note Detection
              </h3>
              <p className="text-[14px] text-[#525252] leading-relaxed">
                High-precision OCR extracts every tolerance value, title block revision, datum symbol, and technical note.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-[#E5E5E5] text-[11px] text-[#A3A3A3]">
              Geometric Optical Extraction
            </div>
          </div>

          <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between hover:border-[#A3A3A3] transition-all shadow-xs group">
            <div>
              <div className="w-10 h-10 rounded-[8px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] group-hover:bg-[#0A0A0A] group-hover:text-white transition-colors mb-4">
                <FileText className="w-5 h-5" />
              </div>
              <h3 className="text-[18px] font-semibold text-[#0A0A0A] mb-2">
                Structured ECO Reports
              </h3>
              <p className="text-[14px] text-[#525252] leading-relaxed">
                Generates exportable, categorized change logs (JSON, PDF, CSV) with sign-off signature blocks.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-[#E5E5E5] text-[11px] text-[#A3A3A3]">
              ISO 10209 & ASME Compliant
            </div>
          </div>

          <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between hover:border-[#A3A3A3] transition-all shadow-xs group">
            <div>
              <div className="w-10 h-10 rounded-[8px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] group-hover:bg-[#0A0A0A] group-hover:text-white transition-colors mb-4">
                <Eye className="w-5 h-5" />
              </div>
              <h3 className="text-[18px] font-semibold text-[#0A0A0A] mb-2">
                Sub-Millimeter Diff Detection
              </h3>
              <p className="text-[14px] text-[#525252] leading-relaxed">
                Color-coded overlay, curtain slider, and split-synchronized views highlight added, cut, and modified geometry.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-[#E5E5E5] text-[11px] text-[#A3A3A3]">
              Synchronized 60fps Pan & Zoom
            </div>
          </div>

          <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between hover:border-[#A3A3A3] transition-all shadow-xs group">
            <div>
              <div className="w-10 h-10 rounded-[8px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] group-hover:bg-[#0A0A0A] group-hover:text-white transition-colors mb-4">
                <Compass className="w-5 h-5" />
              </div>
              <h3 className="text-[18px] font-semibold text-[#0A0A0A] mb-2">
                Symbol & GD&T Recognition
              </h3>
              <p className="text-[14px] text-[#525252] leading-relaxed">
                Automatically identifies true position, concentricity, surface finish markers, and weld callout updates.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-[#E5E5E5] text-[11px] text-[#A3A3A3]">
              ASME Y14.5 Classification
            </div>
          </div>

          <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between hover:border-[#A3A3A3] transition-all shadow-xs group">
            <div>
              <div className="w-10 h-10 rounded-[8px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] group-hover:bg-[#0A0A0A] group-hover:text-white transition-colors mb-4">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-[18px] font-semibold text-[#0A0A0A] mb-2">
                Immutable Audit Trail
              </h3>
              <p className="text-[14px] text-[#525252] leading-relaxed">
                Cryptographic document hashing, reviewer status stamps, and complete revision lineage for QA audits.
              </p>
            </div>
            <div className="mt-5 pt-3 border-t border-[#E5E5E5] text-[11px] text-[#A3A3A3]">
              Enterprise QA Sign-Off
            </div>
          </div>
        </div>
      </section>

      {/* 5. How It Works */}
      <section
        id="how-it-works-section"
        className="w-full bg-[#FAFAFA] border-y border-[#E5E5E5] py-16 sm:py-24"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <span className="text-[11px] font-bold text-[#A3A3A3] uppercase tracking-wider">
              Workflow Pipeline
            </span>
            <h2 className="text-[28px] sm:text-[36px] font-bold text-[#0A0A0A] tracking-tight mt-1">
              How it works in 4 simple steps
            </h2>
            <p className="text-[15px] text-[#525252] mt-3 leading-relaxed">
              From raw CAD exports or scanned PDFs to a finalized Engineering Change Order in under a minute.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between space-y-4 shadow-xs">
              <div>
                <span className="text-[24px] font-bold text-[#0A0A0A] block mb-2">
                  01
                </span>
                <h3 className="text-[16px] font-semibold text-[#0A0A0A] mb-2">
                  Upload Old & New Revision
                </h3>
                <p className="text-[13px] text-[#525252] leading-relaxed">
                  Drag & drop baseline (Rev A) and incoming (Rev B) drawings as PDF, DWG, DXF, or PNG.
                </p>
              </div>
              <div className="text-[11px] text-[#A3A3A3]">
                Multi-format drag & drop
              </div>
            </div>

            <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between space-y-4 shadow-xs">
              <div>
                <span className="text-[24px] font-bold text-[#0A0A0A] block mb-2">
                  02
                </span>
                <h3 className="text-[16px] font-semibold text-[#0A0A0A] mb-2">
                  AI Aligns & Registers Geometry
                </h3>
                <p className="text-[13px] text-[#525252] leading-relaxed">
                  The engine detects datum points, corrects angle tilt, normalizes scales, and maps coordinate spaces.
                </p>
              </div>
              <div className="text-[11px] text-[#A3A3A3]">
                Sub-pixel coordinate registration
              </div>
            </div>

            <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between space-y-4 shadow-xs">
              <div>
                <span className="text-[24px] font-bold text-[#0A0A0A] block mb-2">
                  03
                </span>
                <h3 className="text-[16px] font-semibold text-[#0A0A0A] mb-2">
                  Review Flagged Changes
                </h3>
                <p className="text-[13px] text-[#525252] leading-relaxed">
                  Inspect color-coded deltas in split-view or curtain swipe. Click any table row to auto-zoom to the region.
                </p>
              </div>
              <div className="text-[11px] text-[#A3A3A3]">
                Synchronized 60fps pan/zoom
              </div>
            </div>

            <div className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between space-y-4 shadow-xs">
              <div>
                <span className="text-[24px] font-bold text-[#0A0A0A] block mb-2">
                  04
                </span>
                <h3 className="text-[16px] font-semibold text-[#0A0A0A] mb-2">
                  Export Report & Sign Off
                </h3>
                <p className="text-[13px] text-[#525252] leading-relaxed">
                  Generate formal ISO 10209 Engineering Change Orders (ECO) in PDF format or machine-readable JSON.
                </p>
              </div>
              <div className="text-[11px] text-[#A3A3A3]">
                Print-ready sign-off sheet
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Use Cases / Industries Section */}
      <section
        id="industries-section"
        className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-24"
      >
        <div className="text-center max-w-2xl mx-auto mb-14">
          <span className="text-[11px] font-bold text-[#A3A3A3] uppercase tracking-wider">
            Industry Solutions
          </span>
          <h2 className="text-[28px] sm:text-[36px] font-bold text-[#0A0A0A] tracking-tight mt-1">
            Built for engineering teams across disciplines
          </h2>
          <p className="text-[15px] text-[#525252] mt-3 leading-relaxed">
            Click any discipline below to load an authentic sample dataset directly in the comparison engine.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div
            onClick={onLaunchApp}
            className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between hover:border-[#0A0A0A] hover:shadow-lg transition-all cursor-pointer group"
          >
            <div>
              <div className="w-10 h-10 rounded-[8px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] group-hover:bg-[#0A0A0A] group-hover:text-white transition-colors mb-4">
                <Wrench className="w-5 h-5" />
              </div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-[18px] font-semibold text-[#0A0A0A]">
                  Mechanical & Aerospace
                </h3>
                <span className="text-[11px] text-[#525252] bg-[#FAFAFA] border border-[#E5E5E5] px-2 py-0.5 rounded-[8px]">
                  ASME Y14.5
                </span>
              </div>
              <p className="text-[14px] text-[#525252] leading-relaxed mb-4">
                Flanges, CNC machined housings, crankshafts, and assemblies. Detects bolt pattern shifts, bore tolerances, and fillet radii.
              </p>
            </div>
            <div className="pt-3 border-t border-[#E5E5E5] flex items-center justify-between text-[12px] font-semibold text-[#0A0A0A]">
              <span>Load Mechanical Dataset</span>
              <span>→</span>
            </div>
          </div>

          <div
            onClick={onLaunchApp}
            className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between hover:border-[#0A0A0A] hover:shadow-lg transition-all cursor-pointer group"
          >
            <div>
              <div className="w-10 h-10 rounded-[8px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] group-hover:bg-[#0A0A0A] group-hover:text-white transition-colors mb-4">
                <Building2 className="w-5 h-5" />
              </div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-[18px] font-semibold text-[#0A0A0A]">
                  Architectural & Structural
                </h3>
                <span className="text-[11px] text-[#525252] bg-[#FAFAFA] border border-[#E5E5E5] px-2 py-0.5 rounded-[8px]">
                  AEC / MEP
                </span>
              </div>
              <p className="text-[14px] text-[#525252] leading-relaxed mb-4">
                Floor plans, HVAC ducting, structural grids, and partition walls. Tracks room dimension changes and egress compliance notes.
              </p>
            </div>
            <div className="pt-3 border-t border-[#E5E5E5] flex items-center justify-between text-[12px] font-semibold text-[#0A0A0A]">
              <span>Load Architectural Dataset</span>
              <span>→</span>
            </div>
          </div>

          <div
            onClick={onLaunchApp}
            className="bg-white border border-[#E5E5E5] rounded-[12px] p-6 flex flex-col justify-between hover:border-[#0A0A0A] hover:shadow-lg transition-all cursor-pointer group"
          >
            <div>
              <div className="w-10 h-10 rounded-[8px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] group-hover:bg-[#0A0A0A] group-hover:text-white transition-colors mb-4">
                <Cpu className="w-5 h-5" />
              </div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-[18px] font-semibold text-[#0A0A0A]">
                  Electrical & PCB Schematics
                </h3>
                <span className="text-[11px] text-[#525252] bg-[#FAFAFA] border border-[#E5E5E5] px-2 py-0.5 rounded-[8px]">
                  IPC-7351
                </span>
              </div>
              <p className="text-[14px] text-[#525252] leading-relaxed mb-4">
                Multi-layer PCB layouts, traces, decoupling capacitors, connector pinouts, and test point repositioning.
              </p>
            </div>
            <div className="pt-3 border-t border-[#E5E5E5] flex items-center justify-between text-[12px] font-semibold text-[#0A0A0A]">
              <span>Load Electrical Dataset</span>
              <span>→</span>
            </div>
          </div>
        </div>
      </section>

      {/* 7. Pricing & Payment Section (Ultra-Modern World-Class Design) */}
      <section
        id="pricing-section"
        className="w-full bg-gradient-to-b from-[#FAFAFA] via-white to-[#FAFAFA] border-t border-slate-200/80 py-20 sm:py-28 relative overflow-hidden"
      >
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-gradient-to-tr from-amber-200/20 via-blue-200/20 to-emerald-200/20 rounded-full blur-3xl pointer-events-none -z-10" />

        <div id="payment-section" className="max-w-7xl mx-auto px-4 sm:px-6 relative">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-4 pt-4">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900 text-white text-xs font-medium shadow-sm">
              <CreditCard className="w-4 h-4 text-amber-400" />
              <span className="tracking-wide">Transparent Pricing & Direct Payment</span>
            </div>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
              Simple, flexible plans for engineering teams
            </h2>
            <p className="text-base text-slate-600 leading-relaxed max-w-2xl mx-auto">
              Pay instantly via <strong>bKash Direct Mobile Financial Service (MFS)</strong>.
            </p>

            {/* Monthly / Annual Billing Toggle Switch */}
            <div className="pt-6 flex items-center justify-center gap-4">
              <span className={`text-sm font-medium transition-colors ${billingCycle === 'monthly' ? 'text-slate-900 font-semibold' : 'text-slate-500'}`}>
                Monthly Billing
              </span>
              <button
                type="button"
                role="switch"
                aria-checked={billingCycle === 'annual'}
                onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'annual' : 'monthly')}
                className={`w-14 h-7 rounded-full p-1 relative transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#E2136E] focus:ring-offset-2 ${
                  billingCycle === 'annual' ? 'bg-[#E2136E]' : 'bg-slate-900'
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full transition-transform shadow-md ${
                    billingCycle === 'annual' ? 'translate-x-7' : 'translate-x-0'
                  }`}
                />
              </button>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-medium transition-colors ${billingCycle === 'annual' ? 'text-slate-900 font-semibold' : 'text-slate-500'}`}>
                  Annual Billing
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 text-xs font-semibold border border-emerald-500/20 shadow-2xs">
                  Save 20%
                </span>
              </div>
            </div>
          </div>

          {/* Pricing Tiers Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch max-w-6xl mx-auto">
            {/* Tier 1: Starter */}
            <div className="bg-white border border-slate-200/90 rounded-[12px] p-8 flex flex-col justify-between shadow-[0_10px_30px_-10px_rgba(0,0,0,0.05)] hover:border-slate-300 hover:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.08)] transition-all">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-[0.07em]">
                    Starter
                  </span>
                  <span className="text-xs font-medium text-slate-600 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
                    50 Comparisons / mo
                  </span>
                </div>
                <div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl sm:text-5xl font-extrabold text-[#E2136E] font-mono tracking-tight">
                      {billingCycle === 'annual' ? '৳1,760' : '৳2,200'}
                    </span>
                    <span className="text-sm text-slate-500 font-medium">/month</span>
                  </div>
                  <span className="text-xs text-slate-500 block mt-1.5 font-mono">
                    {billingCycle === 'annual' ? 'Billed annually (৳21,120/yr) • $15 USD' : 'or $19 USD per month'}
                  </span>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Perfect for freelance CAD designers, solo architects, and small revision checks.
                </p>

                <div className="pt-6 border-t border-slate-100 space-y-3">
                  <div className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
                    Included Features:
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.5]" />
                    <span>50 AI drawing comparisons / month</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.5]" />
                    <span>Sub-pixel ORB homography alignment</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.5]" />
                    <span>PDF, DWG & PNG format support</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.5]" />
                    <span>Basic ECO change summary export</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-400">
                    <Check className="w-4 h-4 text-slate-300 shrink-0 stroke-[2.5]" />
                    <span>Standard email support</span>
                  </div>
                </div>
              </div>

              <div className="pt-8">
                <button
                  type="button"
                  onClick={() => handleOpenPayment('starter')}
                  className="w-full py-3.5 bg-[#E2136E] hover:bg-[#C2105E] text-white text-sm font-semibold rounded-xl transition-all shadow-sm hover:shadow-md cursor-pointer flex items-center justify-center gap-2 group active:scale-[0.99]"
                >
                  <span>Pay with bKash</span>
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </button>
                <span className="block text-center text-[11px] text-slate-500 mt-2">
                  Instant bKash MFS checkout
                </span>
              </div>
            </div>

            {/* Tier 2: Professional (Featured Dark Theme) */}
            <div className="bg-[#0F172A] text-white border-2 border-[#E2136E] rounded-[12px] p-8 flex flex-col justify-between shadow-[0_25px_60px_-15px_rgba(226,19,110,0.25)] relative transform lg:-translate-y-3">
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-[#E2136E] text-white text-xs font-extrabold uppercase tracking-wider px-4 py-1.5 rounded-full shadow-lg flex items-center gap-1.5 whitespace-nowrap">
                <Sparkles className="w-3.5 h-3.5 fill-current" />
                <span>Most Popular for QA Teams</span>
              </div>

              <div className="space-y-6 pt-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold text-[#E2136E] uppercase tracking-[0.07em]">
                    Professional
                  </span>
                  <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
                    Unlimited
                  </span>
                </div>
                <div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl sm:text-5xl font-extrabold text-white font-mono tracking-tight">
                      {billingCycle === 'annual' ? '৳7,360' : '৳9,200'}
                    </span>
                    <span className="text-sm text-slate-400 font-medium">/month</span>
                  </div>
                  <span className="text-xs text-[#E2136E]/90 block mt-1.5 font-mono">
                    {billingCycle === 'annual' ? 'Billed annually (৳88,320/yr) • $63 USD' : 'or $79 USD per month'}
                  </span>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">
                  Full suite for engineering departments, QA managers, and manufacturing teams.
                </p>

                <div className="pt-6 border-t border-slate-800 space-y-3">
                  <div className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-3">
                    Everything in Starter, plus:
                  </div>
                  <div className="flex items-center gap-3 text-sm text-white font-medium">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0 stroke-[3]" />
                    <span><strong>Unlimited</strong> AI drawing comparisons</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-white">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0 stroke-[2.5]" />
                    <span>Gemini Flash VLM change classification</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-white">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0 stroke-[2.5]" />
                    <span>ISO 10209 & ASME Y14.5 compliance logs</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-white">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0 stroke-[2.5]" />
                    <span>Annotated PDF & High-Res PNG Export</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-white">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0 stroke-[2.5]" />
                    <span>Multi-page PDF auto page-matching</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-white">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0 stroke-[2.5]" />
                    <span>Priority 24/7 technical support</span>
                  </div>
                </div>
              </div>

              <div className="pt-8 space-y-2.5">
                <button
                  type="button"
                  onClick={() => handleOpenPayment('pro')}
                  className="w-full py-3.5 bg-[#E2136E] hover:bg-[#C2105E] text-white text-sm font-extrabold rounded-xl transition-all shadow-xl flex items-center justify-center gap-2 cursor-pointer group active:scale-[0.99]"
                >
                  <span>Pay with bKash</span>
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1 stroke-[2.5]" />
                </button>
                <span className="block text-center text-xs text-slate-400">
                  Instant Activation • Encrypted MFS • 30-Day Money-Back
                </span>
              </div>
            </div>

            {/* Tier 3: Enterprise */}
            <div className="bg-white border border-slate-200/90 rounded-[12px] p-8 flex flex-col justify-between shadow-[0_10px_30px_-10px_rgba(0,0,0,0.05)] hover:border-slate-300 hover:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.08)] transition-all">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-[0.07em]">
                    Enterprise
                  </span>
                  <span className="text-xs font-medium text-slate-600 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
                    Team License
                  </span>
                </div>
                <div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl sm:text-5xl font-extrabold text-[#E2136E] font-mono tracking-tight">
                      {billingCycle === 'annual' ? '৳23,120' : '৳28,900'}
                    </span>
                    <span className="text-sm text-slate-500 font-medium">/month</span>
                  </div>
                  <span className="text-xs text-slate-500 block mt-1.5 font-mono">
                    {billingCycle === 'annual' ? 'Billed annually (৳277,440/yr) • $199 USD' : 'or $249 USD per month'}
                  </span>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Dedicated infrastructure & REST API for enterprise manufacturing pipelines.
                </p>

                <div className="pt-6 border-t border-slate-100 space-y-3">
                  <div className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
                    Enterprise Features:
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.5]" />
                    <span>Unlimited seat licenses for team</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.5]" />
                    <span>Full REST API & Python/C++ SDK access</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.5]" />
                    <span>Dedicated CAD server infrastructure</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.5]" />
                    <span>SOC2 & ISO 27001 data confidentiality</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-700">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.5]" />
                    <span>Custom VLM model fine-tuning</span>
                  </div>
                </div>
              </div>

              <div className="pt-8">
                <button
                  type="button"
                  onClick={() => handleOpenPayment('enterprise')}
                  className="w-full py-3.5 bg-[#E2136E] hover:bg-[#C2105E] text-white text-sm font-semibold rounded-xl transition-all shadow-sm hover:shadow-md cursor-pointer flex items-center justify-center gap-2 group active:scale-[0.99]"
                >
                  <span>Pay with bKash</span>
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </button>
                <span className="block text-center text-[11px] text-slate-500 mt-2">
                  Instant bKash MFS checkout
                </span>
              </div>
            </div>
          </div>

          {/* Supported Gateways Banner */}
          <div className="mt-16 p-8 sm:p-10 bg-white border border-slate-200/90 rounded-[12px] shadow-sm flex flex-col md:flex-row items-center justify-between gap-6 max-w-6xl mx-auto">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-[#E2136E] text-white flex items-center justify-center shrink-0 shadow-sm font-extrabold text-lg">
                bK
              </div>
              <div>
                <h4 className="text-base font-bold text-slate-900">
                  bKash Payment Gateway
                </h4>
                <p className="text-xs sm:text-sm text-slate-600 mt-0.5">
                  Instant mobile wallet payment with OTP verification & automated ECO workspace activation.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="px-4 py-2.5 bg-[#E2136E]/10 border border-[#E2136E]/25 rounded-full flex items-center gap-2 text-[#C0105C] text-[13px] font-semibold shadow-2xs cursor-default">
                <Smartphone className="w-4 h-4 text-[#E2136E]" />
                <span>bKash Direct MFS (৳ BDT)</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 8. Full-Width CTA Banner */}
      <section className="w-full bg-[#0A0A0A] text-white py-16 sm:py-20 border-b border-neutral-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center space-y-6">
          <h2 className="text-[30px] sm:text-[40px] font-bold tracking-tight text-white leading-tight">
            Ready to stop reviewing drawings by hand?
          </h2>
          <p className="text-[15px] text-[#A3A3A3] max-w-2xl mx-auto leading-relaxed">
            Upload your baseline and revised engineering drawings today to experience automated geometric diffing in under 3 seconds.
          </p>
          <div className="pt-2 flex flex-wrap items-center justify-center gap-4">
            <button
              id="btn-bottom-cta"
              onClick={onLaunchApp}
              className="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-white hover:bg-[#FAFAFA] text-[#0A0A0A] text-[14px] font-semibold rounded-[9999px] transition-all cursor-pointer shadow-lg hover:shadow-xl active:scale-[0.98]"
            >
              <span>Launch Comparison Tool</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={onLaunchApp}
              className="inline-flex items-center gap-2 px-6 py-3.5 bg-[#171717] hover:bg-neutral-800 text-white text-[14px] font-medium rounded-[9999px] border border-neutral-700 transition-colors cursor-pointer"
            >
              <span>Test Interactive Demo</span>
            </button>
          </div>
        </div>
      </section>

      {/* 9. Four-Column Monochrome Footer */}
      <footer id="docs-section" className="w-full bg-[#FAFAFA] border-t border-[#E5E5E5] pt-14 pb-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            <div className="flex flex-col space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#0A0A0A]">
                Product
              </h4>
              <button
                onClick={() => scrollToSection('features-section')}
                className="text-[13px] text-[#525252] hover:text-[#0A0A0A] text-left transition-colors cursor-pointer"
              >
                Features
              </button>
              <button
                onClick={() => scrollToSection('how-it-works-section')}
                className="text-[13px] text-[#525252] hover:text-[#0A0A0A] text-left transition-colors cursor-pointer"
              >
                How It Works
              </button>
              <button
                onClick={onLaunchApp}
                className="text-[13px] text-[#525252] hover:text-[#0A0A0A] text-left transition-colors cursor-pointer"
              >
                Web Application
              </button>
              <span className="text-[13px] text-[#A3A3A3]">
                Changelog (v2.4.0)
              </span>
            </div>

            <div className="flex flex-col space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#0A0A0A]">
                Company
              </h4>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                About Us
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                Engineering Blog
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                Careers (Hiring CAD Engineers)
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                Press & Media Kit
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                Contact Support
              </span>
            </div>

            <div className="flex flex-col space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#0A0A0A]">
                Resources
              </h4>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                ISO 10209 Standards Guide
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                ASME Y14.5 GD&T Reference
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                REST API Documentation
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                Python / C++ SDK
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                System Status (Operational)
              </span>
            </div>

            <div className="flex flex-col space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#0A0A0A]">
                Legal
              </h4>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                Privacy Policy
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                Terms of Service
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                Security & SOC2 Compliance
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                IP & Data Confidentiality
              </span>
              <span className="text-[13px] text-[#525252] hover:text-[#0A0A0A] cursor-pointer">
                Cookie Preferences
              </span>
            </div>
          </div>

          <div className="pt-8 border-t border-[#E5E5E5] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#737373]">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 bg-[#0A0A0A] rounded-[4px] flex items-center justify-center text-white font-bold text-[10px]">
                Δ
              </div>
              <span className="font-semibold text-[#0A0A0A]">Drawing Diff AI</span>
              <span>© {new Date().getFullYear()} Precision Engineering Systems Inc.</span>
            </div>

            <div className="flex items-center gap-6 font-medium text-[11px]">
              <span className="hover:text-[#0A0A0A] cursor-pointer">LinkedIn</span>
              <span className="hover:text-[#0A0A0A] cursor-pointer">X (Twitter)</span>
              <span className="hover:text-[#0A0A0A] cursor-pointer">GitHub</span>
              <span className="text-[#A3A3A3]">| Made for precision QA</span>
            </div>
          </div>
        </div>
      </footer>

      {/* Sign-In Modal */}
      {isSignInModalOpen && (
        <div
          id="signin-modal-backdrop"
          className="fixed inset-0 bg-[#0A0A0A]/70 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150"
        >
          <div
            id="signin-modal-dialog"
            className="bg-white border border-[#E5E5E5] rounded-[12px] shadow-2xl w-full max-w-md p-6 relative animate-in zoom-in-95 duration-150"
          >
            <button
              onClick={() => setIsSignInModalOpen(false)}
              className="absolute top-4 right-4 p-1.5 rounded-[8px] text-[#A3A3A3] hover:text-[#0A0A0A] hover:bg-[#FAFAFA] border border-transparent hover:border-[#E5E5E5] transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-[#0A0A0A] rounded-[8px] flex items-center justify-center text-white font-bold text-xs">
                Δ
              </div>
              <div>
                <h3 className="text-[17px] font-bold text-[#0A0A0A] leading-tight">
                  Sign in to Drawing Diff AI
                </h3>
                <span className="text-xs text-[#525252]">
                  Access your CAD revision review workspace
                </span>
              </div>
            </div>

            {signedInNotice ? (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-[10px] text-center space-y-1">
                <CheckCircle2 className="w-6 h-6 text-emerald-600 mx-auto" />
                <div className="text-sm font-bold text-emerald-900">Signed In Successfully</div>
                <div className="text-xs text-emerald-700">Redirecting to CAD comparison studio...</div>
              </div>
            ) : (
              <form onSubmit={handleSignInSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-[#0A0A0A] mb-1">
                    Work Email
                  </label>
                  <input
                    type="email"
                    required
                    placeholder="engineer@company.com"
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    className="w-full px-3.5 py-2 text-xs border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#0A0A0A] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#0A0A0A] mb-1">
                    Password / SSO Token
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••••••"
                    defaultValue="demo-cad-pass"
                    className="w-full px-3.5 py-2 text-xs border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#0A0A0A] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A]"
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-[#525252]">
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input type="checkbox" defaultChecked className="rounded text-[#0A0A0A]" />
                    <span>Remember workstation</span>
                  </label>
                  <a href="#docs-section" className="hover:text-[#0A0A0A] underline">
                    SSO Help
                  </a>
                </div>

                <button
                  type="submit"
                  className="w-full py-2.5 bg-[#0A0A0A] hover:bg-black text-white text-xs font-semibold rounded-[9999px] transition-colors cursor-pointer shadow-xs"
                >
                  Continue to Workspace
                </button>

                <div className="pt-2 text-center">
                  <button
                    type="button"
                    onClick={() => {
                      setIsSignInModalOpen(false);
                      onLaunchApp();
                    }}
                    className="text-xs text-[#525252] hover:text-[#0A0A0A] underline cursor-pointer"
                  >
                    Or skip sign-in and open comparison demo
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Payment Success Toast */}
      {paymentSuccessNotice && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#0A0A0A] text-white p-4 rounded-[12px] shadow-2xl border border-neutral-700 flex items-center gap-3 animate-in slide-in-from-bottom-5">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span className="text-xs font-semibold">{paymentSuccessNotice}</span>
          <button
            onClick={() => setPaymentSuccessNotice(null)}
            className="text-[#A3A3A3] hover:text-white p-1 ml-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* Interactive Payment Checkout Modal */}
      <PaymentModal
        isOpen={isPaymentModalOpen}
        onClose={() => setIsPaymentModalOpen(false)}
        planId={selectedPaymentPlan}
        billingCycle={billingCycle}
        onPaymentSuccess={handlePaymentSuccess}
      />
    </div>
  );
};
