import React, { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, RefreshCw, ArrowRight } from 'lucide-react';
import { executeBkashPayment, CheckoutResponse } from '../services/paymentService';

interface PaymentCallbackModalProps {
  paymentID: string;
  onClose: () => void;
  onSuccess: (res: CheckoutResponse) => void;
}

export const PaymentCallbackModal: React.FC<PaymentCallbackModalProps> = ({
  paymentID,
  onClose,
  onSuccess,
}) => {
  const [verifying, setVerifying] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [verifiedResult, setVerifiedResult] = useState<CheckoutResponse | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function verify() {
      try {
        setVerifying(true);
        const res = await executeBkashPayment(paymentID);
        if (isMounted) {
          setVerifiedResult(res);
          onSuccess(res);
        }
      } catch (err: any) {
        if (isMounted) {
          setErrorMsg(err?.message || 'bKash payment verification failed.');
        }
      } finally {
        if (isMounted) setVerifying(false);
      }
    }

    if (paymentID) {
      verify();
    } else {
      setErrorMsg('Invalid payment callback parameters.');
      setVerifying(false);
    }

    return () => {
      isMounted = false;
    };
  }, [paymentID, onSuccess]);

  return (
    <div
      id="payment-callback-modal-backdrop"
      className="fixed inset-0 z-[110] bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="bg-white border border-[#E5E5E5] rounded-[12px] shadow-2xl w-full max-w-lg overflow-hidden p-6 sm:p-8 text-center space-y-6">
        {verifying ? (
          <div className="py-8 space-y-4">
            <div className="w-16 h-16 rounded-full bg-rose-50 border-4 border-rose-100 text-[#E2136E] flex items-center justify-center mx-auto animate-pulse">
              <RefreshCw className="w-8 h-8 animate-spin" />
            </div>
            <div className="space-y-1">
              <h3 className="text-xl font-semibold text-[#0A0A0A]">
                Verifying bKash payment...
              </h3>
              <p className="text-xs text-[#737373] max-w-sm mx-auto">
                Executing checkout & independently querying bKash status endpoint to guarantee payment authenticity.
              </p>
            </div>
          </div>
        ) : verifiedResult ? (
          <div className="space-y-6">
            <div className="w-16 h-16 rounded-full bg-rose-50 border-4 border-rose-100 text-[#E2136E] flex items-center justify-center mx-auto shadow-xs">
              <CheckCircle2 className="w-10 h-10" />
            </div>

            <div className="space-y-1">
              <span className="inline-block px-3 py-1 rounded-md bg-rose-50 text-[#E2136E] border border-rose-200/60 text-[11px] font-semibold tracking-wide uppercase">
                bKash verified success
              </span>
              <h3 className="text-xl font-semibold text-[#0A0A0A] pt-2">
                Subscription upgraded
              </h3>
              <p className="text-xs text-[#525252]">
                Your subscription status is now <strong>Active</strong> in your database account.
              </p>
            </div>

            {/* Receipt Summary Card */}
            <div className="bg-[#FAFAFA] border border-[#E5E5E5] rounded-[12px] p-4 text-left space-y-2.5 font-mono text-xs text-[#0A0A0A]">
              <div className="flex justify-between items-center pb-2 border-b border-[#E5E5E5]">
                <span className="text-[#737373]">Transaction ID (TRX):</span>
                <span className="font-bold text-[#E2136E] bg-white px-2 py-0.5 rounded border border-[#E2136E]/30">
                  {verifiedResult.transaction_id}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#737373]">Gateway:</span>
                <span className="font-semibold text-[#E2136E]">bKash sandbox tokenized</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#737373]">Plan name:</span>
                <span className="font-bold text-[#0A0A0A]">{verifiedResult.plan_name}</span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-[#E5E5E5] text-sm">
                <span className="font-bold text-[#0A0A0A]">Total paid:</span>
                <span className="font-extrabold text-[#E2136E]">
                  {verifiedResult.amount_formatted}
                </span>
              </div>
            </div>

            <button
              onClick={onClose}
              className="w-full py-3.5 bg-[#0A0A0A] hover:bg-[#262626] text-white text-xs font-semibold rounded-[12px] transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Continue to workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="w-16 h-16 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto">
              <XCircle className="w-10 h-10" />
            </div>

            <div className="space-y-1">
              <h3 className="text-xl font-semibold text-[#0A0A0A]">
                Payment verification failed
              </h3>
              <p className="text-xs text-rose-600 max-w-sm mx-auto">
                {errorMsg || 'bKash gateway rejected the transaction signature.'}
              </p>
            </div>

            <button
              onClick={onClose}
              className="w-full py-3 bg-[#0A0A0A] text-white text-xs font-semibold rounded-[12px] cursor-pointer"
            >
              Close & try again
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
