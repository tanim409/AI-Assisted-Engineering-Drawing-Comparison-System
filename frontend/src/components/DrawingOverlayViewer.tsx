import React, { useRef, useState, useEffect, useCallback } from 'react';
import { DrawingFile, ChangeItem, ViewportState } from '../types/comparison';
import { getCategoryConfig } from '../config/categories';
import { ArrowLeftRight, Layers, Crosshair, FileQuestion } from 'lucide-react';

interface DrawingOverlayViewerProps {
  oldDrawing?: DrawingFile;
  newDrawing?: DrawingFile;
  oldImageUrl?: string;
  newImageUrl?: string;
  changes: ChangeItem[];
  viewportState: ViewportState;
  onUpdateViewport: (partial: Partial<ViewportState>) => void;
  selectedChangeId: string | null;
  onSelectChange: (changeId: string) => void;
  onOpenChangeDetails?: (change: ChangeItem) => void;
  mode: 'curtain' | 'overlay';
}

export const DrawingOverlayViewer: React.FC<DrawingOverlayViewerProps> = ({
  oldDrawing,
  newDrawing,
  oldImageUrl,
  newImageUrl,
  changes,
  viewportState,
  onUpdateViewport,
  selectedChangeId,
  onSelectChange,
  onOpenChangeDetails,
  mode,
}) => {
  const isDark = viewportState.invertColors;

  if (!oldDrawing || !newDrawing) {
    return (
      <div
        id="drawing-overlay-viewer"
        className={`border rounded-[12px] overflow-hidden flex flex-col h-[640px] xl:h-[720px] select-none transition-colors shadow-xs ${
          isDark ? 'bg-neutral-950 border-neutral-800' : 'bg-white border-[#E5E5E5]'
        }`}
      >
        <div className="flex-1 flex items-center justify-center text-[#A3A3A3] text-xs font-mono">
          No drawing loaded
        </div>
      </div>
    );
  }

  const containerRef = useRef<HTMLDivElement>(null);
  const [isDraggingPan, setIsDraggingPan] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [isDraggingSlider, setIsDraggingSlider] = useState(false);
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0, percentX: 0, percentY: 0 });

  // Handle Wheel Zoom
  const handleWheel = useCallback(
    (e: WheelEvent) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      const newZoom = Math.min(Math.max(viewportState.zoom * zoomFactor, 0.4), 4.0);
      onUpdateViewport({ zoom: newZoom });
    },
    [viewportState.zoom, onUpdateViewport]
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  // Handle Mouse Events for Pan & Slider Drag
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDraggingPan(true);
    setDragStart({
      x: e.clientX - viewportState.panX,
      y: e.clientY - viewportState.panY,
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const percentX = Math.max(0, Math.min(100, Math.round((x / rect.width) * 100)));
    const percentY = Math.max(0, Math.min(100, Math.round((y / rect.height) * 100)));

    setCursorPos({ x, y, percentX, percentY });

    if (isDraggingSlider) {
      onUpdateViewport({ sliderPos: percentX });
    } else if (isDraggingPan) {
      onUpdateViewport({
        panX: e.clientX - dragStart.x,
        panY: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDraggingPan(false);
    setIsDraggingSlider(false);
  };

  return (
    <div
      id="drawing-overlay-viewer"
      className={`border rounded-[12px] overflow-hidden flex flex-col h-[640px] xl:h-[720px] select-none transition-colors shadow-xs ${
        isDark ? 'bg-neutral-950 border-neutral-800' : 'bg-white border-cyprus/20'
      }`}
    >
      {/* Header Bar */}
      <div
        className={`px-4 py-2 border-b flex items-center justify-between text-xs font-mono ${
          isDark
            ? 'bg-neutral-900 border-neutral-800 text-neutral-200'
            : 'bg-[#FAFAFA] border-[#E5E5E5] text-[#0A0A0A]'
        }`}
      >
        <div className="flex items-center gap-3">
          <span className="font-semibold text-[#0A0A0A] flex items-center gap-1.5">
            {mode === 'curtain' ? (
              <>
                <ArrowLeftRight className="w-3.5 h-3.5 text-[#525252]" />
                <span>Interactive Split Curtain Slider (Swipe left/right)</span>
              </>
            ) : (
              <>
                <Layers className="w-3.5 h-3.5 text-[#525252]" />
                <span>Differential Alpha Overlay ({Math.round(viewportState.overlayOpacity)}% Sensitivity)</span>
              </>
            )}
          </span>
        </div>

        <div className="flex items-center gap-4 text-[#525252] text-[11px]">
          <span className="bg-white px-2 py-0.5 rounded-[4px] text-[#0A0A0A] font-semibold border border-[#E5E5E5]">
            Rev A (Source) vs Rev B (Modified)
          </span>
          <span>{oldDrawing.dimensions}</span>
        </div>
      </div>

      {/* Main Viewport Container */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className={`relative flex-1 overflow-hidden cursor-crosshair ${
          isDark ? 'bg-[#0A0A0A]' : 'bg-white'
        }`}
      >
        {/* Scaled and Panned Canvas Container */}
        <div
          className="absolute inset-0 flex items-center justify-center transition-transform duration-75 ease-out"
          style={{
            transform: `translate(${viewportState.panX}px, ${viewportState.panY}px) scale(${viewportState.zoom})`,
            transformOrigin: 'center center',
          }}
        >
          <div className="relative w-[1000px] h-[700px] shrink-0">
            {/* Mode 1: Curtain Swipe Slider */}
            {mode === 'curtain' && (
              <>
                {/* Background Layer: Rev B (Incoming) */}
                <div className="absolute inset-0">
                  {newImageUrl ? (
                    <img src={newImageUrl} alt={newDrawing.name} className="w-full h-full object-contain pointer-events-none" style={{ backgroundColor: isDark ? '#0D0D0D' : '#FFFFFF', filter: isDark ? undefined : 'grayscale(1)' }} />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center" style={{ backgroundColor: isDark ? '#0D0D0D' : '#F5F5F5' }}>
                      <FileQuestion className="w-10 h-10 text-[#A3A3A3]" />
                    </div>
                  )}
                </div>

                {/* Foreground Layer: Rev A (Clipped to Slider percentage) */}
                <div
                  className="absolute inset-0 overflow-hidden"
                  style={{
                    clipPath: `polygon(0 0, ${viewportState.sliderPos}% 0, ${viewportState.sliderPos}% 100%, 0 100%)`,
                  }}
                >
                  {oldImageUrl ? (
                    <img src={oldImageUrl} alt={oldDrawing.name} className="w-full h-full object-contain pointer-events-none" style={{ backgroundColor: isDark ? '#0D0D0D' : '#FFFFFF', filter: isDark ? undefined : 'grayscale(1)' }} />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center" style={{ backgroundColor: isDark ? '#0D0D0D' : '#F5F5F5' }}>
                      <FileQuestion className="w-10 h-10 text-[#A3A3A3]" />
                    </div>
                  )}
                </div>

                {/* Vertical Divider Line */}
                <div
                  style={{ left: `${viewportState.sliderPos}%` }}
                  className="absolute top-0 bottom-0 w-0.5 bg-[#0A0A0A] shadow-md z-20 pointer-events-none"
                >
                  <div
                    onMouseDown={(e) => {
                      e.stopPropagation();
                      setIsDraggingSlider(true);
                    }}
                    className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-[#0A0A0A] border-2 border-white flex items-center justify-center text-white cursor-ew-resize shadow-md pointer-events-auto"
                  >
                    <ArrowLeftRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </>
            )}

            {/* Mode 2: Differential Alpha Blend */}
            {mode === 'overlay' && (
              <>
                {/* Base Layer: Rev A */}
                <div className="absolute inset-0">
                  {oldImageUrl ? (
                    <img src={oldImageUrl} alt={oldDrawing.name} className="w-full h-full object-contain pointer-events-none" style={{ backgroundColor: isDark ? '#0D0D0D' : '#FFFFFF', filter: isDark ? undefined : 'grayscale(1)' }} />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center" style={{ backgroundColor: isDark ? '#0D0D0D' : '#F5F5F5' }}>
                      <FileQuestion className="w-10 h-10 text-[#A3A3A3]" />
                    </div>
                  )}
                </div>

                {/* Blended Layer: Rev B */}
                <div
                  className="absolute inset-0 mix-blend-difference"
                  style={{ opacity: viewportState.overlayOpacity / 100 }}
                >
                  {newImageUrl ? (
                    <img src={newImageUrl} alt={newDrawing.name} className="w-full h-full object-contain pointer-events-none" style={{ filter: 'grayscale(1) invert(1)' }} />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center" style={{ backgroundColor: '#F5F5F5' }}>
                      <FileQuestion className="w-10 h-10 text-[#A3A3A3]" />
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Change Region Markers */}
            {viewportState.showDiffHighlights &&
              changes
                .filter((change) => change.category !== 'no_change')
                .map((change, index) => {
                  const isSelected = selectedChangeId === change.id;
                  const config = getCategoryConfig(change.category);
                  const displayIndex = index + 1;

                  return (
                    <div
                      key={change.id}
                      id={`overlay-hotspot-${change.id}`}
                      role="button"
                      tabIndex={0}
                      aria-label={`Select ${change.id}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectChange(change.id);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onSelectChange(change.id);
                        }
                      }}
                      style={{
                        left: `${change.region.x}%`,
                        top: `${change.region.y}%`,
                        width: `${change.region.width}%`,
                        height: `${change.region.height}%`,
                      }}
                      className={`absolute rounded-[3px] border-[1.5px] border-dashed transition-all cursor-pointer z-30 ${
                        isSelected
                          ? 'border-[#0A0A0A] border-solid ring-2 ring-[#0A0A0A] ring-offset-1 bg-amber-500/20 scale-105 shadow-md'
                          : `${config.highlightBorder} ${config.highlightBg} hover:border-solid hover:opacity-100`
                      }`}
                    >
                      <button
                        type="button"
                        aria-label={`View details for ${change.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectChange(change.id);
                          onOpenChangeDetails?.(change);
                        }}
                        className={`absolute -top-2.5 -right-2.5 w-5 h-5 rounded-full text-[10px] font-mono font-bold flex items-center justify-center shadow-xs border transition-transform ${
                          isSelected
                            ? 'bg-[#0A0A0A] text-white border-white scale-110'
                            : 'bg-white text-[#0A0A0A] border-[#D4D4D4] hover:scale-110'
                        }`}
                        title={`${change.id}: ${change.category.replace(/_/g, ' ')}`}
                      >
                        <span>{displayIndex}</span>
                      </button>
                    </div>
                  );
                })}
          </div>
        </div>
      </div>

      {/* Footer Bar */}
      <div
        className={`px-4 py-2 border-t flex items-center justify-between text-[11px] font-mono ${
          isDark
            ? 'bg-neutral-900 border-neutral-800 text-neutral-400'
            : 'bg-[#FAFAFA] border-[#E5E5E5] text-[#525252]'
        }`}
      >
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Crosshair className="w-3 h-3" />
            <span>
              X: {cursorPos.percentX}% | Y: {cursorPos.percentY}%
            </span>
          </span>
          <span>Zoom: {Math.round(viewportState.zoom * 100)}%</span>
        </div>

        <div className="flex items-center gap-2">
          <span>Drag central handle to swipe diff</span>
          <span>•</span>
          <span>Scroll to zoom</span>
        </div>
      </div>
    </div>
  );
};
