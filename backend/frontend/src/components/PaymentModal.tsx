import React, { useState } from 'react';
import {
  CreditCard,
  Lock,
  X,
  CheckCircle2,
  ShieldCheck,
  Zap,
  ArrowRight,
  Smartphone,
  Check,
  RefreshCw,
  FileText,
  Building2,
  Sparkles,
} from 'lucide-react';
import { processPaymentCheckout, CheckoutResponse } from '../services/paymentService';

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  planId: 'starter' | 'pro' | 'enterprise';
  billingCycle: 'monthly' | 'annual';
  onPaymentSuccess: (res: CheckoutResponse) => void;
}

export const PaymentModal: React.FC<PaymentModalProps> = ({
  isOpen,
  onClose,
  planId,
  billingCycle,
  onPaymentSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<'stripe' | 'bkash'>('stripe');
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [completedResult, setCompletedResult] = useState<CheckoutResponse | null>(null);

  // Stripe form fields
  const [cardName, setCardName] = useState('Sarah Jenkins');
  const [cardNumber, setCardNumber] = useState('4242 4242 4242 4242');
  const [expMonth, setExpMonth] = useState('12');
  const [expYear, setExpYear] = useState('28');
  const [cvc, setCvc] = useState('888');

  // bKash form fields
  const [bkashStep, setBkashStep] = useState<1 | 2 | 3>(1);
  const [bkashPhone, setBkashPhone] = useState('01712345678');
  const [bkashOtp, setBkashOtp] = useState('789123');
  const [bkashPin, setBkashPin] = useState('12345');

  if (!isOpen) return null;

  const planNames = {
    starter: { name: 'Starter Plan', priceUsd: 19, priceBdt: 2200 },
    pro: { name: 'Professional Plan', priceUsd: 79, priceBdt: 9200 },
    enterprise: { name: 'Enterprise Team', priceUsd: 249, priceBdt: 28900 },
  };

  const currentPlan = planNames[planId] || planNames.pro;
  const isAnnual = billingCycle === 'annual';
  const discountMultiplier = isAnnual ? 0.8 * 12 : 1;
  const finalPriceUsd = (currentPlan.priceUsd * discountMultiplier).toFixed(2);
  const finalPriceBdt = Math.round(currentPlan.priceBdt * discountMultiplier).toLocaleString();

  const handleFillDemoStripe = () => {
    setCardName('Alex Mercer');
    setCardNumber('4242 4242 4242 4242');
    setExpMonth('09');
    setExpYear('29');
    setCvc('123');
  };

  const handleStripeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsProcessing(true);

    try {
      const res = await processPaymentCheckout({
        plan_id: planId,
        billing_cycle: billingCycle,
        payment_method: 'stripe',
        stripe_details: {
          cardholder_name: cardName,
          card_number: cardNumber,
          exp_month: expMonth,
          exp_year: expYear,
          cvc,
        },
      });

      setCompletedResult(res);
      onPaymentSuccess(res);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Payment processing failed. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleBkashSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (bkashStep === 1) {
      if (bkashPhone.length < 11) {
        setErrorMsg('Please enter a valid 11-digit bKash mobile number.');
        return;
      }
      setBkashStep(2);
      return;
    }

    if (bkashStep === 2) {
      if (bkashOtp.length < 4) {
        setErrorMsg('Please enter the 6-digit OTP code sent to your phone.');
        return;
      }
      setBkashStep(3);
      return;
    }

    // Step 3: Complete bKash Payment
    setIsProcessing(true);
    try {
      const res = await processPaymentCheckout({
        plan_id: planId,
        billing_cycle: billingCycle,
        payment_method: 'bkash',
        bkash_details: {
          phone_number: bkashPhone,
          otp: bkashOtp,
          pin: bkashPin,
        },
      });

      setCompletedResult(res);
      onPaymentSuccess(res);
    } catch (err: any) {
      setErrorMsg(err?.message || 'bKash payment failed. Please check your PIN and retry.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div
      id="payment-modal-backdrop"
      className="fixed inset-0 z-[100] bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 overflow-y-auto animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isProcessing) onClose();
      }}
    >
      <div
        id="payment-modal-dialog"
        className="bg-white border border-[#E5E5E5] rounded-[16px] shadow-2xl w-full max-w-xl overflow-hidden relative animate-in zoom-in-95 duration-200 my-auto"
      >
        {/* Modal Close Button */}
        <button
          onClick={onClose}
          disabled={isProcessing}
          className="absolute top-4 right-4 p-1.5 rounded-full text-[#737373] hover:text-[#0A0A0A] hover:bg-[#F5F5F5] transition-colors disabled:opacity-50 cursor-pointer z-10"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Success View */}
        {completedResult ? (
          <div className="p-6 sm:p-8 text-center space-y-6 bg-white">
            <div className="w-16 h-16 rounded-full bg-emerald-100 border-4 border-emerald-50 text-emerald-600 flex items-center justify-center mx-auto shadow-sm">
              <CheckCircle2 className="w-10 h-10" />
            </div>

            <div className="space-y-1">
              <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-mono font-bold uppercase tracking-wider">
                Payment Succeeded
              </span>
              <h3 className="text-2xl font-extrabold text-[#0A0A0A] pt-2">
                Thank you for your subscription!
              </h3>
              <p className="text-xs text-[#525252]">
                Your <strong>{completedResult.plan_name}</strong> is now fully active on your workstation.
              </p>
            </div>

            {/* Receipt Summary Card */}
            <div className="bg-[#FAFAFA] border border-[#E5E5E5] rounded-[12px] p-4 text-left space-y-2.5 font-mono text-xs text-[#0A0A0A]">
              <div className="flex justify-between items-center pb-2 border-b border-[#E5E5E5]">
                <span className="text-[#737373]">Transaction ID:</span>
                <span className="font-bold text-[#0A0A0A] bg-white px-2 py-0.5 rounded border border-[#E5E5E5]">
                  {completedResult.transaction_id}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#737373]">Payment Gateway:</span>
                <span className="font-semibold capitalize flex items-center gap-1">
                  {completedResult.payment_method === 'stripe' ? '💳 Stripe' : '📱 bKash Direct'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#737373]">Billing Period:</span>
                <span className="capitalize">{completedResult.billing_cycle}</span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-[#E5E5E5] text-sm">
                <span className="font-bold text-[#0A0A0A]">Total Paid:</span>
                <span className="font-extrabold text-emerald-700">
                  {completedResult.amount_formatted}
                </span>
              </div>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
              <button
                onClick={onClose}
                className="w-full py-3 bg-[#0A0A0A] hover:bg-[#262626] text-white text-xs font-bold rounded-[9999px] transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>Launch Drawing Diff Workspace</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Header Area */}
            <div className="px-6 py-5 bg-[#FAFAFA] border-b border-[#E5E5E5] flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                    Secure Checkout
                  </span>
                  <span className="text-xs text-[#737373]">
                    {isAnnual ? 'Annual Billing (20% Off)' : 'Monthly Plan'}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-[#0A0A0A] mt-1">
                  Subscribe to {currentPlan.name}
                </h3>
              </div>

              <div className="text-right">
                <span className="text-2xl font-extrabold font-mono text-[#0A0A0A]">
                  {activeTab === 'stripe' ? `$${finalPriceUsd}` : `৳${finalPriceBdt}`}
                </span>
                <span className="text-[11px] text-[#737373] block">
                  {isAnnual ? '/year' : '/month'}
                </span>
              </div>
            </div>

            {/* Payment Method Selector Tabs */}
            <div className="grid grid-cols-2 bg-[#F5F5F5] p-1.5 border-b border-[#E5E5E5] text-xs font-semibold">
              <button
                type="button"
                onClick={() => { setActiveTab('stripe'); setErrorMsg(null); }}
                className={`py-2.5 px-3 rounded-[10px] flex items-center justify-center gap-2 transition-all cursor-pointer ${
                  activeTab === 'stripe'
                    ? 'bg-white text-[#0A0A0A] shadow-xs font-bold border border-[#E5E5E5]'
                    : 'text-[#737373] hover:text-[#0A0A0A]'
                }`}
              >
                <CreditCard className="w-4 h-4 text-blue-600" />
                <span>Stripe (Card / Global)</span>
              </button>

              <button
                type="button"
                onClick={() => { setActiveTab('bkash'); setErrorMsg(null); }}
                className={`py-2.5 px-3 rounded-[10px] flex items-center justify-center gap-2 transition-all cursor-pointer ${
                  activeTab === 'bkash'
                    ? 'bg-white text-[#E2136E] shadow-xs font-bold border border-[#E5E5E5]'
                    : 'text-[#737373] hover:text-[#E2136E]'
                }`}
              >
                <Smartphone className="w-4 h-4 text-[#E2136E]" />
                <span>bKash (MFS Bangladesh)</span>
              </button>
            </div>

            {/* Error Notice */}
            {errorMsg && (
              <div className="mx-6 mt-4 p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-[8px] flex items-start gap-2">
                <X className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* TAB 1: STRIPE GATEWAY FORM */}
            {activeTab === 'stripe' && (
              <form onSubmit={handleStripeSubmit} className="p-6 space-y-4">
                <div className="flex items-center justify-between bg-blue-50/60 border border-blue-200/80 p-3 rounded-[10px] text-xs text-blue-950">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0" />
                    <span>256-bit SSL Encrypted via Stripe Checkout</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleFillDemoStripe}
                    className="text-[11px] font-mono text-blue-700 underline hover:text-blue-900 cursor-pointer"
                  >
                    Auto-fill Demo Card
                  </button>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#0A0A0A] mb-1">
                    Cardholder Full Name
                  </label>
                  <input
                    type="text"
                    required
                    value={cardName}
                    onChange={(e) => setCardName(e.target.value)}
                    placeholder="Jane Doe"
                    className="w-full px-3.5 py-2 text-xs border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#0A0A0A] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#0A0A0A] mb-1 flex items-center justify-between">
                    <span>Card Number</span>
                    <span className="font-mono text-[10px] text-[#737373]">Visa, MasterCard, Amex</span>
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      required
                      value={cardNumber}
                      onChange={(e) => setCardNumber(e.target.value)}
                      placeholder="4242 4242 4242 4242"
                      className="w-full px-3.5 py-2 pl-10 text-xs font-mono border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#0A0A0A] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A]"
                    />
                    <CreditCard className="w-4 h-4 text-[#A3A3A3] absolute left-3 top-2.5" />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-[#0A0A0A] mb-1">
                      Exp Month
                    </label>
                    <input
                      type="text"
                      required
                      maxLength={2}
                      value={expMonth}
                      onChange={(e) => setExpMonth(e.target.value)}
                      placeholder="MM"
                      className="w-full px-3 py-2 text-xs font-mono text-center border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#0A0A0A] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A]"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-[#0A0A0A] mb-1">
                      Exp Year
                    </label>
                    <input
                      type="text"
                      required
                      maxLength={2}
                      value={expYear}
                      onChange={(e) => setExpYear(e.target.value)}
                      placeholder="YY"
                      className="w-full px-3 py-2 text-xs font-mono text-center border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#0A0A0A] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A]"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-[#0A0A0A] mb-1 flex items-center justify-between">
                      <span>CVC</span>
                      <Lock className="w-3 h-3 text-[#A3A3A3]" />
                    </label>
                    <input
                      type="password"
                      required
                      maxLength={4}
                      value={cvc}
                      onChange={(e) => setCvc(e.target.value)}
                      placeholder="123"
                      className="w-full px-3 py-2 text-xs font-mono text-center border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#0A0A0A] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A]"
                    />
                  </div>
                </div>

                <div className="pt-3">
                  <button
                    type="submit"
                    disabled={isProcessing}
                    className="w-full py-3 bg-[#0A0A0A] hover:bg-[#262626] text-white text-xs font-bold rounded-[9999px] transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    {isProcessing ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin text-white" />
                        <span>Processing Stripe Payment...</span>
                      </>
                    ) : (
                      <>
                        <Lock className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Pay ${finalPriceUsd} USD via Stripe</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}

            {/* TAB 2: BKASH GATEWAY FORM */}
            {activeTab === 'bkash' && (
              <form onSubmit={handleBkashSubmit} className="p-6 space-y-4">
                {/* bKash Header Banner */}
                <div className="bg-[#E2136E]/10 border border-[#E2136E]/30 p-3 rounded-[10px] flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-[#E2136E] text-white flex items-center justify-center font-bold text-[10px]">
                      bK
                    </div>
                    <span className="font-semibold text-[#E2136E]">bKash Payment Gateway</span>
                  </div>
                  <span className="font-mono text-[11px] font-bold text-[#E2136E] bg-white px-2 py-0.5 rounded border border-[#E2136E]/30">
                    ৳{finalPriceBdt} BDT
                  </span>
                </div>

                {/* Stepper Indicator */}
                <div className="flex items-center justify-between text-[11px] font-mono text-[#737373] px-2 pt-1 border-b border-[#E5E5E5] pb-3">
                  <span className={bkashStep >= 1 ? 'font-bold text-[#E2136E]' : ''}>1. Account</span>
                  <span>→</span>
                  <span className={bkashStep >= 2 ? 'font-bold text-[#E2136E]' : ''}>2. Verification</span>
                  <span>→</span>
                  <span className={bkashStep === 3 ? 'font-bold text-[#E2136E]' : ''}>3. PIN Confirm</span>
                </div>

                {bkashStep === 1 && (
                  <div className="space-y-3">
                    <label className="block text-xs font-semibold text-[#0A0A0A]">
                      Your bKash Mobile Number
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        required
                        value={bkashPhone}
                        onChange={(e) => setBkashPhone(e.target.value)}
                        placeholder="017XXXXXXXX"
                        className="w-full px-3.5 py-2.5 text-xs font-mono border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#E2136E] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A]"
                      />
                      <Smartphone className="w-4 h-4 text-[#E2136E] absolute right-3 top-3" />
                    </div>
                    <p className="text-[11px] text-[#737373]">
                      Enter your 11-digit bKash account number to initiate instant payment request.
                    </p>
                  </div>
                )}

                {bkashStep === 2 && (
                  <div className="space-y-3">
                    <label className="block text-xs font-semibold text-[#0A0A0A]">
                      bKash Verification Code (OTP)
                    </label>
                    <input
                      type="text"
                      required
                      value={bkashOtp}
                      onChange={(e) => setBkashOtp(e.target.value)}
                      placeholder="Enter 6-digit OTP code"
                      className="w-full px-3.5 py-2.5 text-xs font-mono text-center border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#E2136E] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A]"
                    />
                    <div className="flex justify-between items-center text-[11px] text-[#737373]">
                      <span>Sent to {bkashPhone}</span>
                      <button
                        type="button"
                        onClick={() => setBkashStep(1)}
                        className="text-[#E2136E] underline cursor-pointer"
                      >
                        Change Number
                      </button>
                    </div>
                  </div>
                )}

                {bkashStep === 3 && (
                  <div className="space-y-3">
                    <label className="block text-xs font-semibold text-[#0A0A0A]">
                      Enter bKash PIN
                    </label>
                    <input
                      type="password"
                      required
                      maxLength={5}
                      value={bkashPin}
                      onChange={(e) => setBkashPin(e.target.value)}
                      placeholder="•••••"
                      className="w-full px-3.5 py-2.5 text-xs font-mono text-center tracking-widest border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#E2136E] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A]"
                    />
                    <p className="text-[11px] text-[#737373] text-center">
                      Your PIN is encrypted and sent directly to bKash gateway.
                    </p>
                  </div>
                )}

                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={isProcessing}
                    className="w-full py-3 bg-[#E2136E] hover:bg-[#C2105E] text-white text-xs font-bold rounded-[9999px] transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    {isProcessing ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin text-white" />
                        <span>Verifying bKash PIN...</span>
                      </>
                    ) : (
                      <>
                        <span>
                          {bkashStep === 1 && 'Next: Get bKash OTP'}
                          {bkashStep === 2 && 'Next: Confirm PIN'}
                          {bkashStep === 3 && `Confirm Payment ৳${finalPriceBdt} BDT`}
                        </span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}

            {/* Footer Trust Line */}
            <div className="px-6 py-3 bg-[#FAFAFA] border-t border-[#E5E5E5] flex items-center justify-between text-[11px] font-mono text-[#737373]">
              <span className="flex items-center gap-1">
                <Lock className="w-3 h-3 text-emerald-600" /> Guaranteed Refund Policy
              </span>
              <span>Instant Workspace Access</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
