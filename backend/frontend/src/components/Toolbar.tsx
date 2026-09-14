import React from 'react';
import { ViewMode, ViewportState } from '../types/comparison';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Eye,
  EyeOff,
  Grid,
  Moon,
  Sun,
  Download,
  ClipboardList,
} from 'lucide-react';

interface ToolbarProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  viewportState: ViewportState;
  onUpdateViewport: (partial: Partial<ViewportState>) => void;
  onResetView: () => void;
  onFitToScreen: () => void;
  reportId?: string;
  onExportPdf?: () => void;
  isExporting?: boolean;
  onToggleSummary?: () => void;
  showSummary?: boolean;
}

export const Toolbar: React.FC<ToolbarProps> = ({
  viewMode,
  onViewModeChange,
  viewportState,
  onUpdateViewport,
  onResetView,
  onFitToScreen,
  reportId,
  onExportPdf,
  isExporting = false,
  onToggleSummary,
  showSummary = false,
}) => {
  return (
    <div
      id="comparison-toolbar"
      className="bg-[#FAFAFA] border border-cyprus/20 rounded-[12px] px-3 sm:px-4 py-2 flex flex-wrap items-center justify-between gap-x-4 gap-y-2.5 shadow-xs shrink-0 min-w-0"
    >
      {/* Left: Review Mode Segmented Controls */}
      <div className="flex items-center gap-2.5 shrink-0">
        <span className="text-xs font-medium text-[#525252]">
          Review mode
        </span>
        <div className="flex bg-[#E5E5E5] p-[3px] rounded-[9999px] shrink-0 border border-cyprus/20">
          <button
            id="btn-mode-split"
            onClick={() => onViewModeChange('split')}
            className={`px-3 py-1 text-xs font-medium rounded-[9999px] transition-all cursor-pointer ${
              viewMode === 'split'
                ? 'bg-cyprus text-white shadow-xs'
                : 'text-[#525252] hover:text-[#0A0A0A]'
            }`}
          >
            Split View
          </button>

          <button
            id="btn-mode-curtain"
            onClick={() => onViewModeChange('curtain')}
            className={`px-3 py-1 text-xs font-medium rounded-[9999px] transition-all cursor-pointer ${
              viewMode === 'curtain'
                ? 'bg-cyprus text-white shadow-xs'
                : 'text-[#525252] hover:text-[#0A0A0A]'
            }`}
          >
            Curtain Swipe
          </button>

          <button
            id="btn-mode-overlay"
            onClick={() => onViewModeChange('overlay')}
            className={`px-3 py-1 text-xs font-medium rounded-[9999px] transition-all cursor-pointer ${
              viewMode === 'overlay'
                ? 'bg-cyprus text-white shadow-xs'
                : 'text-[#525252] hover:text-[#0A0A0A]'
            }`}
          >
            Overlay Diff
          </button>
        </div>
      </div>

      {/* Middle: Mode Specific Controls (Sensitivity / Slider / Opacity) */}
      <div className="flex items-center gap-4 text-[12px] shrink-0">
        {viewMode === 'curtain' && (
          <div className="flex items-center gap-2">
            <span className="text-[#525252] text-xs font-medium">Curtain position:</span>
            <div className="w-28 sm:w-32 h-1 bg-[#E5E5E5] relative rounded-full flex items-center">
              <div
                className="absolute top-0 left-0 h-full bg-[#0A0A0A] rounded-full"
                style={{ width: `${viewportState.sliderPos}%` }}
              />
              <input
                type="range"
                min="0"
                max="100"
                value={viewportState.sliderPos}
                onChange={(e) => onUpdateViewport({ sliderPos: Number(e.target.value) })}
                className="absolute inset-0 opacity-0 cursor-ew-resize w-full"
              />
              <div
                className="absolute top-[-4px] w-3 h-3 bg-white border border-[#0A0A0A] rounded-full shadow-xs pointer-events-none -translate-x-1/2"
                style={{ left: `${viewportState.sliderPos}%` }}
              />
            </div>
            <span className="font-mono text-[#A3A3A3] text-xs">
              {Math.round(viewportState.sliderPos)}%
            </span>
          </div>
        )}

        {viewMode === 'overlay' && (
          <div className="flex items-center gap-2">
            <span className="text-[#525252] text-xs font-medium">Diff sensitivity:</span>
            <div className="w-28 sm:w-32 h-1 bg-[#E5E5E5] relative rounded-full flex items-center">
              <div
                className="absolute top-0 left-0 h-full bg-[#0A0A0A] rounded-full"
                style={{ width: `${viewportState.overlayOpacity}%` }}
              />
              <input
                type="range"
                min="0"
                max="100"
                value={viewportState.overlayOpacity}
                onChange={(e) => onUpdateViewport({ overlayOpacity: Number(e.target.value) })}
                className="absolute inset-0 opacity-0 cursor-pointer w-full"
              />
              <div
                className="absolute top-[-4px] w-3 h-3 bg-white border border-[#0A0A0A] rounded-full shadow-xs pointer-events-none -translate-x-1/2"
                style={{ left: `${viewportState.overlayOpacity}%` }}
              />
            </div>
            <span className="font-mono text-[#A3A3A3] text-xs">
              {Math.round(viewportState.overlayOpacity)}%
            </span>
          </div>
        )}

        {viewMode === 'split' && (
          <div className="flex items-center gap-2">
            <span className="text-[#525252] text-xs font-medium">Synchronized view:</span>
            <button
              id="btn-toggle-sync"
              onClick={() => onUpdateViewport({ isSynced: !viewportState.isSynced })}
              className={`px-2.5 py-1 rounded-[6px] text-xs font-medium border transition-colors cursor-pointer ${
                viewportState.isSynced
                  ? 'bg-white text-[#0A0A0A] border-[#E5E5E5] shadow-xs'
                  : 'bg-transparent text-[#525252] border-transparent'
              }`}
            >
              {viewportState.isSynced ? 'Locked (1:1)' : 'Independent'}
            </button>
          </div>
        )}
      </div>

      {/* Right: Actions (Summary & Export PDF) & Viewport Controls */}
      <div className="flex flex-wrap items-center gap-2 shrink-0">
        {onToggleSummary && (
          <button
            id="btn-toggle-summary-toolbar"
            onClick={onToggleSummary}
            title="Toggle Review Summary"
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-[9999px] border transition-colors cursor-pointer shadow-xs ${
              showSummary
                ? 'bg-cyprus text-white border-cyprus'
                : 'bg-white hover:bg-[#FAFAFA] text-[#525252] hover:text-[#0A0A0A] border-[#E5E5E5]'
            }`}
          >
            <ClipboardList className="w-3.5 h-3.5" />
            <span>Summary</span>
          </button>
        )}

        {onExportPdf && (
          <button
            id="btn-export-pdf-toolbar"
            onClick={onExportPdf}
            disabled={!reportId || isExporting}
            title={reportId ? 'Download annotated diff PDF' : 'Export requires a saved report'}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-cyprus hover:bg-cyprus-deep disabled:opacity-50 text-white text-xs font-semibold rounded-[9999px] transition-colors cursor-pointer shadow-xs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{isExporting ? 'Exporting…' : 'Export PDF'}</span>
          </button>
        )}

        <div className="h-4 w-[1px] bg-[#E5E5E5] mx-0.5" />

        <div className="flex items-center gap-1">
          {/* Zoom Readout */}
          <span className="text-[11px] font-mono text-[#525252] px-2 py-1 bg-white rounded-[6px] border border-[#E5E5E5]">
            {Math.round(viewportState.zoom * 100)}%
          </span>

          {/* Zoom In */}
          <button
            id="btn-zoom-in"
            onClick={() => onUpdateViewport({ zoom: Math.min(viewportState.zoom + 0.25, 4.0) })}
            className="p-1.5 rounded-[6px] bg-white border border-[#E5E5E5] text-[#525252] hover:text-[#0A0A0A] hover:bg-[#F5F5F5] transition-colors cursor-pointer"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>

          {/* Zoom Out */}
          <button
            id="btn-zoom-out"
            onClick={() => onUpdateViewport({ zoom: Math.max(viewportState.zoom - 0.25, 0.4) })}
            className="p-1.5 rounded-[6px] bg-white border border-[#E5E5E5] text-[#525252] hover:text-[#0A0A0A] hover:bg-[#F5F5F5] transition-colors cursor-pointer"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>

          {/* Fit to Screen */}
          <button
            id="btn-fit-screen"
            onClick={onFitToScreen}
            className="p-1.5 rounded-[6px] bg-white border border-[#E5E5E5] text-[#525252] hover:text-[#0A0A0A] hover:bg-[#F5F5F5] transition-colors cursor-pointer"
            title="Fit Drawing to Screen"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>

          {/* Reset Viewport */}
          <button
            id="btn-reset-view"
            onClick={onResetView}
            className="p-1.5 rounded-[6px] bg-white border border-[#E5E5E5] text-[#525252] hover:text-[#0A0A0A] hover:bg-[#F5F5F5] transition-colors cursor-pointer"
            title="Reset Pan & Zoom"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="h-4 w-[1px] bg-[#E5E5E5] mx-0.5" />

        <div className="flex items-center gap-1">
          {/* Diff Highlights Toggle */}
          <button
            id="btn-toggle-diff-highlights"
            onClick={() =>
              onUpdateViewport({
                showDiffHighlights: !viewportState.showDiffHighlights,
              })
            }
            className={`p-1.5 rounded-[6px] border transition-colors cursor-pointer ${
              viewportState.showDiffHighlights
                ? 'bg-[#0A0A0A] text-white border-[#0A0A0A]'
                : 'bg-white text-[#525252] border-[#E5E5E5] hover:text-[#0A0A0A]'
            }`}
            title={
              viewportState.showDiffHighlights
                ? 'Hide Change Overlays'
                : 'Show Change Overlays'
            }
          >
            {viewportState.showDiffHighlights ? (
              <Eye className="w-3.5 h-3.5" />
            ) : (
              <EyeOff className="w-3.5 h-3.5" />
            )}
          </button>

          {/* CAD Grid Toggle */}
          <button
            id="btn-toggle-cad-grid"
            onClick={() =>
              onUpdateViewport({ showCADGrid: !viewportState.showCADGrid })
            }
            className={`p-1.5 rounded-[6px] border transition-colors cursor-pointer ${
              viewportState.showCADGrid
                ? 'bg-[#0A0A0A] text-white border-[#0A0A0A]'
                : 'bg-white text-[#525252] border-[#E5E5E5] hover:text-[#0A0A0A]'
            }`}
            title="Toggle CAD Grid & Zone Rulers"
          >
            <Grid className="w-3.5 h-3.5" />
          </button>

          {/* Blueprint Dark Mode Toggle */}
          <button
            id="btn-toggle-blueprint-mode"
            onClick={() =>
              onUpdateViewport({ invertColors: !viewportState.invertColors })
            }
            className="p-1.5 rounded-[6px] bg-white border border-[#E5E5E5] text-[#525252] hover:text-[#0A0A0A] hover:bg-[#F5F5F5] transition-colors cursor-pointer"
            title={
              viewportState.invertColors
                ? 'Switch to Light Paper Mode'
                : 'Switch to Dark CAD Blueprint Mode'
            }
          >
            {viewportState.invertColors ? (
              <Sun className="w-3.5 h-3.5" />
            ) : (
              <Moon className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
