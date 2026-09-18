import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  ShieldCheck,
  ArrowRight,
  Smartphone,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { createBkashPayment, CheckoutResponse } from '../services/paymentService';

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
  const [payerPhone, setPayerPhone] = useState('01711111111');
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [completedResult, setCompletedResult] = useState<CheckoutResponse | null>(null);

  if (!isOpen) return null;

  const planNames = {
    starter: { name: 'Starter Plan', priceBdt: 2200, priceUsd: 19 },
    pro: { name: 'Professional Plan', priceBdt: 9200, priceUsd: 79 },
    enterprise: { name: 'Enterprise Team', priceBdt: 28900, priceUsd: 249 },
  };

  const currentPlan = planNames[planId] || planNames.pro;
  const isAnnual = billingCycle === 'annual';
  const discountMultiplier = isAnnual ? 0.8 * 12 : 1;
  const rawPriceBdt = currentPlan.priceBdt * (isAnnual ? 12 : 1);
  const finalPriceBdt = Math.round(currentPlan.priceBdt * discountMultiplier).toLocaleString();
  const finalPriceUsd = (currentPlan.priceUsd * discountMultiplier).toFixed(2);

  const handleReset = () => {
    setErrorMsg(null);
    setIsProcessing(false);
    setCompletedResult(null);
  };

  const handleCloseModal = () => {
    handleReset();
    onClose();
  };

  const handleInitiateBkashCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsProcessing(true);

    try {
      const res = await createBkashPayment(planId, billingCycle, payerPhone);

      if (res.bkashURL) {
        window.location.href = res.bkashURL;
      } else {
        throw new Error('bKash checkout URL not returned by server.');
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to connect to bKash checkout gateway. Please try again.');
      setIsProcessing(false);
    }
  };

  return (
    <div
      id="payment-modal-backdrop"
      className="fixed inset-0 z-[100] bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 overflow-y-auto animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isProcessing) handleCloseModal();
      }}
    >
      <div
        id="payment-modal-dialog"
        className="bg-white border border-[#E5E5E5] rounded-[12px] shadow-2xl w-full max-w-lg overflow-hidden relative animate-in zoom-in-95 duration-200 my-auto"
      >
        {/* Modal Close Button */}
        <button
          onClick={handleCloseModal}
          disabled={isProcessing}
          className="absolute top-4 right-4 p-1.5 rounded-full text-[#737373] hover:text-[#0A0A0A] hover:bg-[#F5F5F5] transition-colors disabled:opacity-50 cursor-pointer z-10"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Completed View */}
        {completedResult ? (
          <div className="p-6 sm:p-8 text-center space-y-6 bg-white">
            <div className="w-16 h-16 rounded-full bg-rose-50 border-4 border-rose-100 text-[#E2136E] flex items-center justify-center mx-auto shadow-xs">
              <CheckCircle2 className="w-10 h-10" />
            </div>

            <div className="space-y-1">
              <span className="inline-block px-3 py-1 rounded-md bg-rose-50 text-[#E2136E] border border-rose-200/60 text-[11px] font-semibold tracking-wide uppercase">
                bKash verified success
              </span>
              <h3 className="text-xl font-semibold text-[#0A0A0A] pt-2">
                Subscription activated
              </h3>
              <p className="text-xs text-[#525252]">
                Your <strong>{completedResult.plan_name}</strong> is now active in your workspace.
              </p>
            </div>

            {/* Receipt Summary Card */}
            <div className="bg-[#FAFAFA] border border-[#E5E5E5] rounded-[12px] p-4 text-left space-y-2.5 font-mono text-xs text-[#0A0A0A]">
              <div className="flex justify-between items-center pb-2 border-b border-[#E5E5E5]">
                <span className="text-[#737373]">Transaction ID (TRX):</span>
                <span className="font-bold text-[#E2136E] bg-white px-2 py-0.5 rounded border border-[#E2136E]/30">
                  {completedResult.transaction_id}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#737373]">Gateway:</span>
                <span className="font-semibold text-[#E2136E]">bKash tokenized checkout</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#737373]">Billing period:</span>
                <span className="capitalize">{completedResult.billing_cycle}</span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-[#E5E5E5] text-sm">
                <span className="font-bold text-[#0A0A0A]">Total amount verified:</span>
                <span className="font-extrabold text-[#E2136E]">
                  {completedResult.amount_formatted}
                </span>
              </div>
            </div>

            <button
              onClick={handleCloseModal}
              className="w-full py-3.5 bg-[#0A0A0A] hover:bg-[#262626] text-white text-xs font-semibold rounded-[12px] transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Launch drawing diff workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <>
            {/* Header Area */}
            <div className="pl-6 pr-12 py-5 bg-[#FAFAFA] border-b border-[#E5E5E5] flex items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="inline-block px-2.5 py-0.5 rounded-md bg-rose-50 text-[#E2136E] border border-rose-200/60 text-[11px] font-medium tracking-wide uppercase">
                    BKASH TOKENIZED SANDBOX
                  </span>
                </div>
                <h3 className="text-[19px] font-semibold text-[#0A0A0A] tracking-tight pt-0.5">
                  Subscribe to {currentPlan.name}
                </h3>
              </div>

              {/* Price section with clear strikethrough & spaced USD equivalent */}
              <div className="text-right flex flex-col items-end shrink-0">
                <div className="flex items-baseline gap-2 justify-end">
                  {isAnnual && (
                    <span className="text-xs text-[#737373] line-through font-mono">
                      ৳{rawPriceBdt.toLocaleString()}
                    </span>
                  )}
                  <span className="text-xl sm:text-2xl font-bold font-mono text-[#0A0A0A]">
                    ৳{finalPriceBdt}
                  </span>
                </div>
                <span className="text-xs text-[#737373] mt-0.5 block">
                  {isAnnual ? '/year' : '/month'} (${finalPriceUsd})
                </span>
              </div>
            </div>

            {/* bKash Header Banner */}
            <div className="bg-[#E2136E] text-white px-6 py-2.5 flex items-center justify-between text-xs font-medium">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-white text-[#E2136E] flex items-center justify-center font-bold text-[11px] shadow-xs">
                  bK
                </div>
                <span>bKash Tokenized Checkout</span>
              </div>
              <span className="font-mono text-[11px] bg-white/20 px-2 py-0.5 rounded">
                ৳{finalPriceBdt} BDT
              </span>
            </div>

            {/* Clean Error Banner — only shown if errorMsg is set */}
            {errorMsg && (
              <div className="mx-6 mt-4 p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-[12px] flex items-start gap-2">
                <X className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* bKash Checkout Form */}
            <form onSubmit={handleInitiateBkashCheckout} className="p-6 space-y-4">
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[#0A0A0A]">
                  bKash Account / Reference Phone (Optional)
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={payerPhone}
                    onChange={(e) => setPayerPhone(e.target.value)}
                    placeholder="01711111111"
                    className="w-full px-3.5 py-3 text-xs font-mono border border-[#E5E5E5] rounded-[12px] focus:outline-none focus:border-[#E2136E] bg-[#FAFAFA] focus:bg-white text-[#0A0A0A] transition-all"
                  />
                  <Smartphone className="w-4 h-4 text-[#737373] absolute right-3.5 top-3.5" />
                </div>
                <p className="text-[13px] text-[#525252] leading-relaxed pt-1">
                  Clicking <strong>Pay with bKash</strong> will open bKash's official tokenized checkout portal to complete payment.
                </p>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isProcessing}
                  id="pay-with-bkash-btn"
                  className="w-full py-3.5 px-6 bg-[#E2136E] hover:bg-[#C2105E] text-white text-sm font-semibold rounded-[12px] transition-all shadow-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isProcessing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-white" />
                      <span>Initiating bKash gateway...</span>
                    </>
                  ) : (
                    <>
                      <div className="w-5 h-5 rounded-full bg-white text-[#E2136E] flex items-center justify-center font-bold text-[10px]">
                        bK
                      </div>
                      <span>Pay with bKash (৳{finalPriceBdt} BDT)</span>
                      <ExternalLink className="w-4 h-4 ml-1" />
                    </>
                  )}
                </button>
              </div>
            </form>

            <div className="px-6 py-3 bg-[#FAFAFA] border-t border-[#E5E5E5] flex items-center justify-between text-[11px] font-mono text-[#737373]">
              <span className="flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-[#E2136E]" /> bKash Sandbox API v1.2.0
              </span>
              <span>Double Verified Execution</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
