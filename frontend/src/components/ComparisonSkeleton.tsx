import React from 'react';

interface ComparisonSkeletonProps {
  progressMessage?: string | null;
  onCancel?: () => void;
}

export const ComparisonSkeleton: React.FC<ComparisonSkeletonProps> = ({ progressMessage, onCancel }) => {
  return (
    <div id="comparison-skeleton-view" className="w-full space-y-4 animate-pulse">
      {/* Live job progress bar */}
      <div className="bg-white border border-[#E5E5E5] rounded-[12px] px-6 py-4 flex flex-wrap items-center justify-between gap-3 shadow-xs">
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neutral-400 opacity-60"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#0A0A0A]"></span>
          </span>
          <div>
            <div className="text-sm font-semibold text-[#0A0A0A]">Comparing drawings…</div>
            <div className="text-xs font-mono text-[#525252]">
              {progressMessage || 'Queued — waiting for the comparison engine'}
            </div>
          </div>
        </div>
        {onCancel && (
          <button
            id="btn-cancel-compare"
            onClick={onCancel}
            className="px-4 py-2 bg-white hover:bg-[#FAFAFA] text-[#525252] hover:text-[#0A0A0A] text-xs font-medium rounded-[9999px] border border-[#E5E5E5] transition-colors cursor-pointer"
          >
            Cancel
          </button>
        )}
      </div>
      {/* Top Meta & Toolbar Skeleton */}
      <div className="bg-white border border-neutral-200 rounded-md p-3.5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-5 w-48 bg-neutral-200 rounded" />
          <div className="h-5 w-20 bg-neutral-100 rounded" />
          <div className="h-5 w-24 bg-neutral-100 rounded" />
        </div>
        <div className="flex items-center gap-2">
          <div className="h-8 w-24 bg-neutral-200 rounded" />
          <div className="h-8 w-24 bg-neutral-100 rounded" />
          <div className="h-8 w-8 bg-neutral-100 rounded" />
          <div className="h-8 w-8 bg-neutral-100 rounded" />
          <div className="h-8 w-28 bg-neutral-200 rounded" />
        </div>
      </div>

      {/* Side-by-Side Drawing Panels Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Panel Skeleton (Rev A) */}
        <div className="bg-white border border-neutral-200 rounded-md overflow-hidden flex flex-col h-[520px]">
          <div className="px-4 py-2.5 bg-neutral-50 border-b border-neutral-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-4 w-28 bg-neutral-200 rounded" />
              <div className="h-4 w-16 bg-neutral-200 rounded" />
            </div>
            <div className="h-4 w-20 bg-neutral-200 rounded" />
          </div>

          <div className="flex-1 p-6 bg-neutral-100/60 relative flex items-center justify-center">
            {/* Shimmer CAD Drawing Profile Simulation */}
            <div className="w-4/5 h-3/5 border-2 border-dashed border-neutral-300 rounded flex flex-col items-center justify-center gap-3">
              <div className="w-2/3 h-6 bg-neutral-200 rounded" />
              <div className="w-1/2 h-4 bg-neutral-200/80 rounded" />
              <div className="w-3/4 h-24 bg-neutral-200/50 rounded" />
            </div>

            {/* Rulers skeleton */}
            <div className="absolute top-2 left-2 right-2 h-3 bg-neutral-200/50 rounded" />
            <div className="absolute top-2 bottom-2 left-2 w-3 bg-neutral-200/50 rounded" />
          </div>

          <div className="px-3 py-2 bg-neutral-50 border-t border-neutral-200 flex items-center justify-between">
            <div className="h-3 w-32 bg-neutral-200 rounded" />
            <div className="h-3 w-20 bg-neutral-200 rounded" />
          </div>
        </div>

        {/* Right Panel Skeleton (Rev B) */}
        <div className="bg-white border border-neutral-200 rounded-md overflow-hidden flex flex-col h-[520px]">
          <div className="px-4 py-2.5 bg-neutral-50 border-b border-neutral-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-4 w-28 bg-neutral-200 rounded" />
              <div className="h-4 w-16 bg-neutral-200 rounded" />
            </div>
            <div className="h-4 w-20 bg-neutral-200 rounded" />
          </div>

          <div className="flex-1 p-6 bg-neutral-100/60 relative flex items-center justify-center">
            {/* Shimmer CAD Drawing Profile Simulation */}
            <div className="w-4/5 h-3/5 border-2 border-dashed border-neutral-300 rounded flex flex-col items-center justify-center gap-3">
              <div className="w-2/3 h-6 bg-neutral-200 rounded" />
              <div className="w-1/2 h-4 bg-neutral-200/80 rounded" />
              <div className="w-3/4 h-24 bg-neutral-200/50 rounded" />
            </div>

            {/* Rulers skeleton */}
            <div className="absolute top-2 left-2 right-2 h-3 bg-neutral-200/50 rounded" />
            <div className="absolute top-2 bottom-2 left-2 w-3 bg-neutral-200/50 rounded" />
          </div>

          <div className="px-3 py-2 bg-neutral-50 border-t border-neutral-200 flex items-center justify-between">
            <div className="h-3 w-32 bg-neutral-200 rounded" />
            <div className="h-3 w-20 bg-neutral-200 rounded" />
          </div>
        </div>
      </div>

      {/* Report Table Skeleton */}
      <div className="bg-white border border-neutral-200 rounded-md p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-5 w-36 bg-neutral-200 rounded" />
            <div className="h-5 w-16 bg-neutral-100 rounded" />
          </div>
          <div className="flex items-center gap-2">
            <div className="h-8 w-48 bg-neutral-100 rounded" />
            <div className="h-8 w-24 bg-neutral-100 rounded" />
          </div>
        </div>

        {/* Category filters skeleton */}
        <div className="flex items-center gap-2">
          <div className="h-6 w-16 bg-neutral-200 rounded" />
          <div className="h-6 w-24 bg-neutral-100 rounded" />
          <div className="h-6 w-28 bg-neutral-100 rounded" />
          <div className="h-6 w-20 bg-neutral-100 rounded" />
        </div>

        {/* Table Rows Skeleton */}
        <div className="border border-neutral-200 rounded overflow-hidden">
          <div className="h-10 bg-neutral-100 border-b border-neutral-200 flex items-center px-4 gap-4">
            <div className="h-3 w-16 bg-neutral-300 rounded" />
            <div className="h-3 w-24 bg-neutral-300 rounded" />
            <div className="h-3 w-32 bg-neutral-300 rounded" />
            <div className="h-3 w-24 bg-neutral-300 rounded" />
            <div className="h-3 w-24 bg-neutral-300 rounded" />
            <div className="h-3 w-20 bg-neutral-300 rounded" />
          </div>

          {[1, 2, 3, 4, 5].map((row) => (
            <div
              key={row}
              className="h-14 border-b border-neutral-100 flex items-center px-4 gap-4"
            >
              <div className="h-4 w-16 bg-neutral-200 rounded" />
              <div className="h-5 w-24 bg-neutral-200 rounded" />
              <div className="h-4 w-40 bg-neutral-200 rounded" />
              <div className="h-4 w-28 bg-neutral-100 rounded" />
              <div className="h-4 w-28 bg-neutral-200 rounded" />
              <div className="h-4 w-20 bg-neutral-100 rounded ml-auto" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
