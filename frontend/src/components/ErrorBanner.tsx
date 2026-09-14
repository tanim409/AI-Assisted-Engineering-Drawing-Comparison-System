import React, { useState } from 'react';
import { ComparisonError } from '../types/comparison';
import { AlertTriangle, RefreshCw, UploadCloud, ChevronDown, ChevronUp, Terminal } from 'lucide-react';

interface ErrorBannerProps {
  error: ComparisonError;
  onRetry: () => void;
  onReupload: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  error,
  onRetry,
  onReupload,
}) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  // Status code styling tag
  const statusBadge = error.statusCode ? `HTTP ${error.statusCode}` : 'NETWORK FAULT';

  return (
    <div
      id="comparison-error-banner"
      className="w-full max-w-3xl mx-auto my-8 border border-[#E5E5E5] bg-white rounded-[12px] p-6 shadow-xs animate-in fade-in duration-200"
    >
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 rounded-[10px] bg-[#FAFAFA] border border-[#E5E5E5] flex items-center justify-center text-[#0A0A0A] shrink-0 mt-0.5">
          <AlertTriangle className="w-5 h-5 text-amber-600" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-[8px] bg-[#FAFAFA] text-[#525252] border border-[#E5E5E5]">
              {statusBadge}
            </span>
            <h3 className="text-[18px] font-semibold text-[#0A0A0A] tracking-tight">
              {error.title}
            </h3>
          </div>

          <p className="text-[15px] text-[#525252] leading-relaxed mb-3">
            {error.message}
          </p>

          {error.suggestedAction && (
            <p className="text-[13px] text-[#525252] leading-normal mb-5 bg-[#FAFAFA] p-3.5 rounded-[8px] border border-[#E5E5E5]">
              <span className="font-semibold text-[#0A0A0A]">Recommended Action: </span>
              {error.suggestedAction}
            </p>
          )}

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-3">
            {error.retryable && (
              <button
                id="btn-error-retry"
                onClick={onRetry}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#0A0A0A] hover:bg-[#171717] text-white text-xs font-semibold rounded-[9999px] transition-colors cursor-pointer shadow-xs"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Comparison</span>
              </button>
            )}

            <button
              id="btn-error-reupload"
              onClick={onReupload}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-white hover:bg-[#FAFAFA] text-[#0A0A0A] text-xs font-semibold border border-[#E5E5E5] rounded-[9999px] transition-colors cursor-pointer"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Select Different Files</span>
            </button>

            {error.technicalDetails && (
              <button
                id="btn-toggle-diagnostics"
                onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs text-[#525252] hover:text-[#0A0A0A] transition-colors ml-auto cursor-pointer"
              >
                <Terminal className="w-3.5 h-3.5 text-[#A3A3A3]" />
                <span>{showTechnicalDetails ? 'Hide Diagnostics' : 'View Diagnostics'}</span>
                {showTechnicalDetails ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>
            )}
          </div>

          {/* Collapsible Diagnostic Trace */}
          {showTechnicalDetails && error.technicalDetails && (
            <div className="mt-4 pt-3 border-t border-[#E5E5E5] animate-in fade-in duration-150">
              <div className="text-[11px] font-mono text-[#525252] mb-1">
                ENGINEERING TELEMETRY LOG:
              </div>
              <pre className="text-xs font-mono bg-[#0A0A0A] text-[#FAFAFA] p-3.5 rounded-[8px] overflow-x-auto whitespace-pre-wrap leading-relaxed select-all border border-[#E5E5E5]">
                {`[Telemetry Trace ID: ${Date.now().toString(36).toUpperCase()}]\n`}
                {`Error Code: ${error.type}\n`}
                {`HTTP Status: ${error.statusCode || 'N/A'}\n`}
                {`Kernel Detail: ${error.technicalDetails}\n`}
                {`Logged to client diagnostic sink: true`}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
