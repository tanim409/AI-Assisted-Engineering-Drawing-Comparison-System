/**
 * Engineering Drawing Comparison Tool — Root application
 * Handles authentication gating, page routing, and the main comparison workspace.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  AsyncState,
  ComparisonResult,
  ComparisonError,
  DrawingFile,
  ViewMode,
  ViewportState,
  ChangeReviewStatus,
  ChangeItem,
} from './types/comparison';
import { runDrawingComparison } from './services/comparisonService';
import { uploadAndCompare } from './services/drawingService';
import { fetchReviewsSummary, submitChangeReview } from './services/reviewService';
import { ReviewSummary } from './types/comparison';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AuthPage } from './components/AuthPage';
import { AuthToast } from './components/AuthToast';
import { Header } from './components/Header';
import { LandingPage } from './components/LandingPage';
import { UploadZone } from './components/UploadZone';
import { ComparisonSkeleton } from './components/ComparisonSkeleton';
import { DrawingPanel } from './components/DrawingPanel';
import { DrawingOverlayViewer } from './components/DrawingOverlayViewer';
import { DrawingLibrary } from './components/DrawingLibrary';
import { QaChatPanel } from './components/QaChatPanel';
import { Toolbar } from './components/Toolbar';
import { ErrorBanner } from './components/ErrorBanner';
import { ChangeDetailsModal } from './components/ChangeDetailsModal';
import { RightDetailPanel } from './components/RightDetailPanel';
import { NavigationToolbar } from './components/NavigationToolbar';
import { PaymentCallbackModal } from './components/PaymentCallbackModal';
import { CheckoutResponse } from './services/paymentService';
import { ErrorBoundary } from './components/ErrorBoundary';


// ─── Root with AuthProvider ───────────────────────────────────────────────────

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </ErrorBoundary>
  );
}

// ─── AppShell — auth gate + page routing ─────────────────────────────────────

function AppShell() {
  const { isAuthenticated, isLoading } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authTab, setAuthTab] = useState<'login' | 'register'>('login');
  const [authToast, setAuthToast] = useState<{ visible: boolean; message: string }>({
    visible: false,
    message: '',
  });

  // Called by any protected feature when the user is not logged in
  const requestLogin = useCallback((message = 'Please log in to use this feature.') => {
    setAuthToast({ visible: true, message });
  }, []);

  useEffect(() => {
    const handleAuthExpired = (e: Event) => {
      const msg = (e as CustomEvent)?.detail?.message || 'Authentication required. Please log in to continue.';
      requestLogin(msg);
    };
    window.addEventListener('auth:expired', handleAuthExpired);
    return () => window.removeEventListener('auth:expired', handleAuthExpired);
  }, [requestLogin]);

  const openAuthModal = useCallback((tab: 'login' | 'register' = 'login') => {
    setAuthTab(tab);
    setShowAuthModal(true);
  }, []);

  const closeAuthModal = useCallback(() => setShowAuthModal(false), []);

  const dismissToast = useCallback(() =>
    setAuthToast((prev) => ({ ...prev, visible: false })), []);

  // bKash callback route detection (/payment-callback?paymentID=...&status=...)
  const [bkashCallbackPaymentID, setBkashCallbackPaymentID] = useState<string | null>(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const paymentID = searchParams.get('paymentID');
    const isCallback = window.location.pathname.includes('/payment-callback') || !!paymentID;
    return isCallback && paymentID ? paymentID : null;
  });

  const handleClosePaymentCallback = useCallback(() => {
    window.history.replaceState({}, '', '/');
    setBkashCallbackPaymentID(null);
  }, []);

  // Show a full-screen spinner while we validate the stored JWT
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-2 border-white/10 border-t-white/60 rounded-full animate-spin" />
          <p className="text-white/40 text-sm">Verifying session…</p>
        </div>
      </div>
    );
  }


  return (
    <>
      <MainApp
        onLoggedOut={closeAuthModal}
        requestLogin={requestLogin}
        onOpenAuthModal={openAuthModal}
      />

      {bkashCallbackPaymentID && (
        <PaymentCallbackModal
          paymentID={bkashCallbackPaymentID}
          onClose={handleClosePaymentCallback}
          onSuccess={(res) => {
            console.log('[bKash Success Callback Verified]:', res);
          }}
        />
      )}

      {/* Auth modal — only mounts when the Login button is clicked */}
      {showAuthModal && !isAuthenticated && (
        <div
          id="auth-modal-overlay"
          className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center px-4"
          onClick={(e) => { if (e.target === e.currentTarget) closeAuthModal(); }}
        >
          <div className="relative w-full max-w-md">
            <button
              id="auth-modal-close"
              onClick={closeAuthModal}
              className="absolute -top-3 -right-3 z-10 w-8 h-8 bg-white/10 hover:bg-white/20 border border-white/20 rounded-full flex items-center justify-center text-white/60 hover:text-white transition-colors"
              aria-label="Close"
            >
              ✕
            </button>
            <AuthPage
              onAuthenticated={closeAuthModal}
              initialTab={authTab}
              onClose={closeAuthModal}
            />
          </div>
        </div>
      )}

      {/* Auth required toast */}
      <AuthToast
        message={authToast.message}
        isVisible={authToast.visible}
        onClose={dismissToast}
        onLoginClick={() => openAuthModal('login')}
      />
    </>
  );
}

// ─── MainApp — the full comparison workspace ──────────────────────────────────

function MainApp({
  onLoggedOut,
  requestLogin,
  onOpenAuthModal,
}: {
  onLoggedOut: () => void;
  requestLogin: (message?: string) => void;
  onOpenAuthModal: (tab?: 'login' | 'register') => void;
}) {
  // Page View Switcher ('landing' | 'app' | 'library')
  const [pageView, setPageView] = useState<'landing' | 'app' | 'library'>('landing');

  // Async Three-State Machine (idle -> loading -> success | error)
  const [asyncState, setAsyncState] = useState<AsyncState>('idle');
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<ComparisonError | null>(null);

  // Feature 1: async job progress + cancellation
  const [jobProgress, setJobProgress] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Persisted review state for the current report
  const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(null);
  const currentReportRef = useRef<string | null>(null);

  // Stored request options for retry capability
  const [lastRequestOptions, setLastRequestOptions] = useState<{
    oldFile: Partial<DrawingFile> | File;
    newFile: Partial<DrawingFile> | File;
    simulatedError?: '422_ALIGNMENT_FAILED' | '500_SERVER_ERROR' | 'NETWORK_TIMEOUT' | null;
  } | null>(null);

  // Viewport & View Mode State
  const [viewMode, setViewMode] = useState<ViewMode>('split');
  const [viewportState, setViewportState] = useState<ViewportState>({
    zoom: 1.0,
    panX: 0,
    panY: 0,
    isSynced: true,
    sliderPos: 50,
    overlayOpacity: 65,
    showDiffHighlights: true,
    showCADGrid: true,
    invertColors: false,
    selectedChangeId: null,
    hoveredChangeId: null,
  });

  const [detailChange, setDetailChange] = useState<ChangeItem | null>(null);

  const handleUpdateViewport = useCallback((partial: Partial<ViewportState>) => {
    setViewportState((prev) => ({ ...prev, ...partial }));
  }, []);

  const handleResetView = useCallback(() => {
    setViewportState((prev) => ({
      ...prev,
      zoom: 1.0,
      panX: 0,
      panY: 0,
      sliderPos: 50,
    }));
  }, []);

  const handleFitToScreen = useCallback(() => {
    setViewportState((prev) => ({
      ...prev,
      zoom: 0.9,
      panX: 0,
      panY: 0,
    }));
  }, []);

  const refreshReviewSummary = useCallback(async (reportId: string) => {
    try {
      const summary = await fetchReviewsSummary(reportId);
      if (currentReportRef.current === reportId) setReviewSummary(summary);
    } catch {
      // Summary is best-effort; the table falls back to local counts.
    }
  }, []);



  const applyNewResult = useCallback((comparisonResult: ComparisonResult) => {
    currentReportRef.current = comparisonResult.reportId ?? null;
    setReviewSummary(null);
    setResult(comparisonResult);
    setAsyncState('success');
    setJobProgress(null);
    setViewportState((prev) => ({
      ...prev,
      zoom: 1.0,
      panX: 0,
      panY: 0,
      selectedChangeId: null,
    }));
    if (comparisonResult.reportId) {
      void refreshReviewSummary(comparisonResult.reportId);
    }
  }, [refreshReviewSummary]);

  const { isAuthenticated } = useAuth();

  const handleStartComparison = async (
    oldFile: Partial<DrawingFile> | File,
    newFile: Partial<DrawingFile> | File,
    simulatedError?: '422_ALIGNMENT_FAILED' | '500_SERVER_ERROR' | 'NETWORK_TIMEOUT' | null
  ) => {
    if (!isAuthenticated) {
      requestLogin('Please log in to align and compare engineering drawings.');
      return;
    }

    setPageView('app');
    setLastRequestOptions({ oldFile, newFile, simulatedError });
    setError(null);
    setAsyncState('loading');
    setJobProgress('Queued — waiting for the comparison engine');

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      setJobProgress('Queued — sending drawings to AI backend...');
      let comparisonResult: ComparisonResult;
      if (!simulatedError && oldFile instanceof File && newFile instanceof File) {
        const res = await uploadAndCompare(oldFile, newFile, undefined, undefined, undefined, {
          onJobProgress: (job) => {
            if (job.progress_message) setJobProgress(job.progress_message);
          },
          abortSignal: controller.signal,
        });
        comparisonResult = res.result;
      } else {
        comparisonResult = await runDrawingComparison({
          old_drawing: oldFile,
          new_drawing: newFile,
          simulateError: simulatedError,
          onJobProgress: (job) => {
            if (job.progress_message) setJobProgress(job.progress_message);
          },
          abortSignal: controller.signal,
        });
      }

      applyNewResult(comparisonResult);
    } catch (err: any) {
      setJobProgress(null);
      setError(err as ComparisonError);
      setAsyncState('error');
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  };

  const handleCancelComparison = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const handleLoadComparison = useCallback(
    (comparisonResult: ComparisonResult) => {
      setPageView('app');
      setLastRequestOptions(null);
      setError(null);
      applyNewResult(comparisonResult);
    },
    [applyNewResult]
  );

  const handleRetry = () => {
    if (!lastRequestOptions) return;
    handleStartComparison(
      lastRequestOptions.oldFile,
      lastRequestOptions.newFile,
      lastRequestOptions.simulatedError
    );
  };

  const handleResetToUpload = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    currentReportRef.current = null;
    setAsyncState('idle');
    setResult(null);
    setError(null);
    setJobProgress(null);
    setReviewSummary(null);
  };

  const [isExporting, setIsExporting] = useState(false);

  const handleExportPdf = async () => {
    if (!result?.reportId || isExporting) return;
    setIsExporting(true);
    try {
      const { downloadSummaryPdf } = await import('./services/comparisonService');
      await downloadSummaryPdf(result.reportId);
    } catch {
      // Fallback if summary PDF unavailable
      try {
        const { downloadAnnotatedPdf } = await import('./services/comparisonService');
        await downloadAnnotatedPdf(result.reportId);
      } catch {
        // Export failed
      }
    } finally {
      setIsExporting(false);
    }
  };

  const [rightPanelTab, setRightPanelTab] = useState<'changes' | 'summary'>('changes');

  // State for Right-Side Panel & Navigation Filter
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(true);
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState('all');

  const handleToggleSummary = useCallback(() => {
    setRightPanelTab((prev) => (prev === 'summary' ? 'changes' : 'summary'));
    setIsRightPanelOpen(true);
  }, []);

  const handleSelectChange = (changeId: string) => {
    if (!result) return;
    const targetChange = result.changes.find((c) => c.id === changeId);
    if (!targetChange) return;

    // Ensure right side detail panel expands when a change is selected
    if (!isRightPanelOpen) {
      setIsRightPanelOpen(true);
    }
    // Also switch to changes tab when selecting a change
    setRightPanelTab('changes');

    const targetX = (targetChange.region.x + targetChange.region.width / 2 - 50) * -7;
    const targetY = (targetChange.region.y + targetChange.region.height / 2 - 50) * -5;
    setViewportState((prev) => ({
      ...prev,
      selectedChangeId: changeId,
      zoom: 1.6,
      panX: targetX,
      panY: targetY,
    }));
  };

  const handleStatusChange = async (changeId: string, status: ChangeReviewStatus) => {
    if (!result) return;
    const target = result.changes.find((c) => c.id === changeId);
    if (!target) return;

    // Toggle status: if clicking the current status again, revert to 'pending'
    const newStatus: ChangeReviewStatus = target.status === status ? 'pending' : status;

    if (
      target.reportId != null &&
      target.pageNumber != null &&
      target.changeIndex != null &&
      (newStatus === 'approved' || newStatus === 'flagged' || newStatus === 'pending')
    ) {
      try {
        await submitChangeReview(target.reportId, target.pageNumber, target.changeIndex, newStatus);
        await refreshReviewSummary(target.reportId);
      } catch {
        // Persist failed — keep the optimistic local update.
      }
    }

    setResult((prev) => {
      if (!prev) return null;
      const updatedChanges = prev.changes.map((c) =>
        c.id === changeId ? { ...c, status: newStatus } : c
      );

      const confirmed = updatedChanges.filter((c) => c.status === 'approved').length;
      const false_positive = updatedChanges.filter((c) => c.status === 'flagged').length;
      const unreviewed = updatedChanges.filter(
        (c) => c.status === 'pending' || c.status === 'unreviewed' || !c.status
      ).length;

      setReviewSummary((oldSummary) => ({
        report_id: oldSummary?.report_id || target.reportId || '',
        total_changes: updatedChanges.length,
        confirmed,
        false_positive,
        unreviewed,
        unreviewed_changes: oldSummary?.unreviewed_changes || [],
      }));

      return {
        ...prev,
        changes: updatedChanges,
      };
    });

    setDetailChange((prev) => (prev && prev.id === changeId ? { ...prev, status: newStatus } : prev));
  };

  const handleLogout = useCallback(() => {
    onLoggedOut();
    setPageView('landing');
    handleResetToUpload();
  }, [onLoggedOut]);

  useEffect(() => {
    const handleOpenComparison = () => setPageView('app');
    window.addEventListener('nav:open-comparison', handleOpenComparison);
    return () => window.removeEventListener('nav:open-comparison', handleOpenComparison);
  }, []);

  // Derived: true when the comparison workspace is the active view
  const isComparisonWorkspace = pageView === 'app' && asyncState === 'success' && !!result;

  // Lock <html> scroll when the comparison workspace is open so the CAD canvas
  // never scrolls off screen — restore scrolling for all other views.
  useEffect(() => {
    if (isComparisonWorkspace) {
      document.documentElement.classList.add('viewport-locked');
    } else {
      document.documentElement.classList.remove('viewport-locked');
    }
    return () => {
      document.documentElement.classList.remove('viewport-locked');
    };
  }, [isComparisonWorkspace]);

  // Landing page
  if (pageView === 'landing') {
    return (
      <LandingPage
        onLaunchApp={() => {
          handleResetToUpload();
          setPageView('app');
        }}
        onOpenAuthModal={onOpenAuthModal}
      />
    );
  }

  return (
    <div className={`bg-vanilla text-neutral-900 flex flex-col font-sans antialiased selection:bg-neutral-900 selection:text-white ${
      isComparisonWorkspace ? 'h-screen overflow-hidden' : 'min-h-screen'
    }`}>
      {/* Top Header Navigation */}
      <Header
        result={result}
        asyncState={asyncState}
        reviewSummary={reviewSummary}
        onResetToUpload={handleResetToUpload}
        onNavigateToLanding={() => setPageView('landing')}
        onOpenLibrary={() => setPageView('library')}
        onLoggedOut={handleLogout}
        onOpenAuthModal={onOpenAuthModal}
        onRequestLogin={requestLogin}
      />

      {/* Main Content Area */}
      <main className={`flex-1 w-full max-w-[1800px] mx-auto flex flex-col min-h-0 ${
        isComparisonWorkspace ? 'p-3 overflow-hidden' : 'px-4 sm:px-6 py-4'
      }`}>
        {/* Drawing Library view */}
        {pageView === 'library' && (
          <DrawingLibrary
            onLoadComparison={handleLoadComparison}
            onClose={() => setPageView(result ? 'app' : 'landing')}
          />
        )}

        {pageView === 'app' && (
          <>
            {/* State 1: Upload Screen */}
            {asyncState === 'idle' && (
              <UploadZone onStartComparison={handleStartComparison} isComparing={asyncState === 'loading'} />
            )}

            {/* State 2: Processing Skeleton Screen */}
            {asyncState === 'loading' && (
              <ComparisonSkeleton progressMessage={jobProgress} onCancel={handleCancelComparison} />
            )}

            {/* State 3: Error State Banner */}
            {asyncState === 'error' && error && (
              <ErrorBanner
                error={error}
                onRetry={handleRetry}
                onReupload={handleResetToUpload}
              />
            )}

            {/* State 4: Active Viewport-Locked Comparison & Review Screen */}
            {asyncState === 'success' && result && (
              <div className="flex-1 flex flex-col gap-3 min-h-0 overflow-x-auto">
                <div className="flex-1 flex flex-col gap-3 min-h-0 min-w-[980px]">
                  {/* Fixed Top Toolbar */}
                  <Toolbar
                    viewMode={viewMode}
                    onViewModeChange={setViewMode}
                    viewportState={viewportState}
                    onUpdateViewport={handleUpdateViewport}
                    onResetView={handleResetView}
                    onFitToScreen={handleFitToScreen}
                    reportId={result.reportId}
                    onExportPdf={handleExportPdf}
                    isExporting={isExporting}
                    onToggleSummary={handleToggleSummary}
                    showSummary={rightPanelTab === 'summary'}
                  />

                  {/* Viewport-Locked Split Layout: Left Drawing Canvas Container + Right Detail Sidebar */}
                  <div className="flex-1 flex gap-3 items-stretch min-h-0 overflow-hidden">
                    {/* Left Column: Bounded CAD Drawing Canvas Container */}
                    <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden border border-[#E5E5E5] rounded-[12px] bg-white shadow-xs">
                      {/* CAD Viewport Header Bar containing Navigation Toolbar */}
                      <div className="px-4 py-2 bg-[#FAFAFA] border-b border-[#E5E5E5] flex flex-wrap items-center justify-between shrink-0 gap-3">
                        <div className="flex items-center gap-2 font-mono text-xs font-bold text-[#0A0A0A] shrink-0">
                          <span className="w-2 h-2 rounded-full bg-amber-500" />
                          <span>CAD VIEWPORT</span>
                        </div>

                        <NavigationToolbar
                          changes={result.changes}
                          selectedChangeId={viewportState.selectedChangeId}
                          onSelectChange={handleSelectChange}
                          selectedCategoryFilter={selectedCategoryFilter}
                          onCategoryFilterChange={setSelectedCategoryFilter}
                        />
                      </div>

                      {/* CAD Viewport Area (Split or Overlay) */}
                      <div className="flex-1 relative flex flex-col min-w-0 h-full overflow-hidden p-2 bg-[#FAFAFA]">
                        {viewMode === 'split' ? (
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 flex-1 h-full min-h-0 overflow-hidden">
                            <DrawingPanel
                              drawing={result.oldDrawing}
                              revisionType="A"
                              imageUrl={result.oldDrawingUrl}
                              changes={result.changes}
                              viewportState={viewportState}
                              onUpdateViewport={handleUpdateViewport}
                              selectedChangeId={viewportState.selectedChangeId}
                              onSelectChange={handleSelectChange}
                            />
                            <DrawingPanel
                              drawing={result.newDrawing}
                              revisionType="B"
                              imageUrl={result.newDrawingUrl}
                              changes={result.changes}
                              viewportState={viewportState}
                              onUpdateViewport={handleUpdateViewport}
                              selectedChangeId={viewportState.selectedChangeId}
                              onSelectChange={handleSelectChange}
                              isSecondaryPanel
                            />
                          </div>
                        ) : (
                          <DrawingOverlayViewer
                            oldDrawing={result.oldDrawing}
                            newDrawing={result.newDrawing}
                            oldImageUrl={result.oldDrawingUrl}
                            newImageUrl={result.newDrawingUrl}
                            changes={result.changes}
                            viewportState={viewportState}
                            onUpdateViewport={handleUpdateViewport}
                            selectedChangeId={viewportState.selectedChangeId}
                            onSelectChange={handleSelectChange}
                            mode={viewMode}
                          />
                        )}
                      </div>
                    </div>

                    {/* Right Column: Independently Bounded Side Panel */}
                    <RightDetailPanel
                      changes={result.changes}
                      selectedChangeId={viewportState.selectedChangeId}
                      onSelectChange={handleSelectChange}
                      onStatusChange={handleStatusChange}
                      isOpen={isRightPanelOpen}
                      onToggleOpen={() => setIsRightPanelOpen(!isRightPanelOpen)}
                      selectedCategoryFilter={selectedCategoryFilter}
                      onCategoryFilterChange={setSelectedCategoryFilter}
                      reviewSummary={reviewSummary}
                      activeTab={rightPanelTab}
                      onTabChange={setRightPanelTab}
                      overallSummary={result.overallSummary}
                      overallSimilarity={result.overallSimilarity}
                      totalRegionsDetected={result.totalRegionsDetected}
                    />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {asyncState === 'success' && result && (
        <QaChatPanel
          reportId={result.reportId}
          changes={result.changes}
          onSelectChange={handleSelectChange}
        />
      )}
    </div>
  );
}
