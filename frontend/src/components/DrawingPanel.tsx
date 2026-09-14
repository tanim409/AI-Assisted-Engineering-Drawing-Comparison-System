import React, { useRef, useState, useEffect, useCallback } from 'react';
import { DrawingFile, ChangeItem, ViewportState } from '../types/comparison';
import { getCategoryConfig } from '../config/categories';
import { Crosshair, FileQuestion } from 'lucide-react';

interface DrawingPanelProps {
  drawing?: DrawingFile;
  revisionType: 'A' | 'B';
  imageUrl?: string;
  changes: ChangeItem[];
  viewportState: ViewportState;
  onUpdateViewport: (partial: Partial<ViewportState>) => void;
  selectedChangeId: string | null;
  onSelectChange: (changeId: string) => void;
  onOpenChangeDetails?: (change: ChangeItem) => void;
  isSecondaryPanel?: boolean;
}

export const DrawingPanel: React.FC<DrawingPanelProps> = ({
  drawing,
  revisionType,
  imageUrl,
  changes,
  viewportState,
  onUpdateViewport,
  selectedChangeId,
  onSelectChange,
  onOpenChangeDetails,
  isSecondaryPanel = false,
}) => {
  if (!drawing) {
    return (
      <div
        id={`drawing-panel-${revisionType}`}
        className="border border-cyprus/20 rounded-[10px] overflow-hidden flex flex-col h-[640px] xl:h-[720px] select-none transition-colors shadow-[0_1px_3px_rgba(0,0,0,0.04)]"
      >
        <div className="flex-1 flex items-center justify-center text-[#A3A3A3] text-xs font-mono">
          No drawing loaded
        </div>
      </div>
    );
  }

  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isZooming, setIsZooming] = useState(false);
  const zoomIdleRef = useRef<number | null>(null);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0, percentX: 0, percentY: 0 });
  const [hoveredRegionChange, setHoveredRegionChange] = useState<ChangeItem | null>(null);

  // CAD zone labels
  const horizontalZones = ['1', '2', '3', '4', '5', '6', '7', '8'];
  const verticalZones = ['A', 'B', 'C', 'D', 'E', 'F'];

  // Handle Pan Dragging
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
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
    const percentX = Math.round((x / rect.width) * 100);
    const percentY = Math.round((y / rect.height) * 100);

    setCursorPos({ x, y, percentX, percentY });

    if (isDragging) {
      const newPanX = e.clientX - dragStart.x;
      const newPanY = e.clientY - dragStart.y;
      onUpdateViewport({ panX: newPanX, panY: newPanY });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Wheel zoom handler (also flags the panel as actively interacting)
  const handleWheel = useCallback(
    (e: WheelEvent) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      const newZoom = Math.min(Math.max(viewportState.zoom * zoomFactor, 0.4), 4.0);
      onUpdateViewport({ zoom: newZoom });
      setIsZooming(true);
      if (zoomIdleRef.current !== null) window.clearTimeout(zoomIdleRef.current);
      zoomIdleRef.current = window.setTimeout(() => {
        setIsZooming(false);
        zoomIdleRef.current = null;
      }, 350);
    },
    [viewportState.zoom, onUpdateViewport]
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  useEffect(() => {
    return () => {
      if (zoomIdleRef.current !== null) window.clearTimeout(zoomIdleRef.current);
    };
  }, []);

  const isDark = viewportState.invertColors;
  // Accent-keyed container borders: Source/Baseline (A) → Cyprus,
  // Modified/Current (B) → emerald. No background fills or tints — the
  // border line is the only accent.
  const accentBorder = revisionType === 'A' ? 'border-cyprus' : 'border-emerald-500';
  const accentBorderHover = revisionType === 'A' ? 'hover:border-cyprus-deep' : 'hover:border-emerald-600';
  const accentBorderActive = revisionType === 'A' ? 'border-cyprus-deep' : 'border-emerald-600';
  const accentRing = revisionType === 'A' ? 'ring-cyprus/50' : 'ring-emerald-500/50';
  const isInteracting = isDragging || isZooming;

  return (
    <div
      id={`drawing-panel-${revisionType}`}
      className={`border rounded-[10px] overflow-hidden flex flex-col h-[640px] xl:h-[720px] select-none transition-colors transition-shadow ${
        isDark
          ? 'bg-neutral-950 border-neutral-800 shadow-none'
          : `bg-white ${accentBorder} shadow-[0_1px_3px_rgba(0,0,0,0.04)] ${accentBorderHover}`
      } ${!isDark && isInteracting ? `${accentBorderActive} ring-2 ring-inset ${accentRing}` : ''}`}
    >
      {/* Header Bar */}
      <div
        className={`px-4 py-2 border-b flex items-center justify-between text-xs ${
          isDark
            ? 'bg-neutral-900 border-neutral-800 text-neutral-200'
            : 'bg-[#FAFAFA] border-[#E5E5E5] text-[#0A0A0A]'
        }`}
      >
        <div className="flex items-center gap-2.5">
          <span
            className={`px-3 py-1 rounded-full text-xs font-bold tracking-wide transition-all shadow-2xs flex items-center gap-1.5 ${
              revisionType === 'A'
                ? 'bg-blue-600 text-white border border-blue-700 shadow-blue-500/20'
                : 'bg-emerald-600 text-white border border-emerald-700 shadow-emerald-500/20'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${revisionType === 'A' ? 'bg-blue-200' : 'bg-emerald-200'}`} />
            {revisionType === 'A' ? 'Source · Baseline' : 'Modified · Current'}
          </span>
          <span className="font-semibold text-xs sm:text-sm truncate max-w-[220px]" title={drawing.name}>
            {drawing.name}
          </span>
        </div>

        <div className="flex items-center gap-3 text-[#737373] text-[11px]">
          <span>{drawing.dimensions}</span>
          <span>•</span>
          <span className="font-mono">{drawing.fileSize}</span>
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
        {/* CAD Zone Rulers (Top & Left) */}
        {viewportState.showCADGrid && (
          <>
            {/* Top Horizontal Ruler */}
            <div
              className={`absolute top-0 left-6 right-0 h-5 border-b flex items-center justify-around text-[11px] font-mono z-10 pointer-events-none ${
                isDark
                  ? 'bg-neutral-900/90 border-neutral-800 text-neutral-400'
                  : 'bg-white/90 border-[#E5E5E5] text-[#525252]'
              }`}
            >
              {horizontalZones.map((zone) => (
                <span key={zone} className="flex-1 text-center border-r border-[#E5E5E5] last:border-0">
                  {zone}
                </span>
              ))}
            </div>

            {/* Left Vertical Ruler */}
            <div
              className={`absolute top-5 left-0 bottom-0 w-6 border-r flex flex-col justify-around text-[11px] font-mono z-10 pointer-events-none ${
                isDark
                  ? 'bg-neutral-900/90 border-neutral-800 text-neutral-400'
                  : 'bg-white/90 border-[#E5E5E5] text-[#525252]'
              }`}
            >
              {verticalZones.map((zone) => (
                <span key={zone} className="flex-1 flex items-center justify-center border-b border-[#E5E5E5] last:border-0">
                  {zone}
                </span>
              ))}
            </div>
          </>
        )}

        {/* Scaled & Panned Drawing Layer */}
        <div
          className="absolute inset-0 flex items-center justify-center transition-transform duration-75 ease-out"
          style={{
            transform: `translate(${viewportState.panX}px, ${viewportState.panY}px) scale(${viewportState.zoom})`,
            transformOrigin: 'center center',
          }}
        >
          <div className="relative w-[1000px] h-[700px] shrink-0">
            {/* Actual uploaded drawing image */}
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={drawing.name}
                className="w-full h-full object-contain select-none pointer-events-none"
                style={{
                  backgroundColor: isDark ? '#0D0D0D' : '#FFFFFF',
                  // Force neutral grayscale in light mode so sepia/paper-tinted
                  // scans always render as black/white line drawings.
                  filter: isDark ? undefined : 'grayscale(1)',
                }}
              />
            ) : (
              <div
                className="w-full h-full flex flex-col items-center justify-center gap-3"
                style={{ backgroundColor: isDark ? '#0D0D0D' : '#F5F5F5' }}
              >
                <FileQuestion className="w-12 h-12 text-[#6b7280]" />
                <span className="text-[13px] text-[#6b7280]">No preview available</span>
              </div>
            )}

            {/* Highlighted Change Overlays & Bounding Boxes */}
            {viewportState.showDiffHighlights &&
              changes
                .filter((change) => change.category !== 'no_change')
                .map((change, index) => {
                  const isSelected = selectedChangeId === change.id;
                  const isHovered = hoveredRegionChange?.id === change.id;
                  const config = getCategoryConfig(change.category);
                  const displayIndex = index + 1;

                  return (
                    <div
                      key={change.id}
                      id={`hotspot-${revisionType}-${change.id}`}
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
                      onMouseEnter={() => setHoveredRegionChange(change)}
                      onMouseLeave={() => setHoveredRegionChange(null)}
                      style={{
                        left: `${change.region.x}%`,
                        top: `${change.region.y}%`,
                        width: `${change.region.width}%`,
                        height: `${change.region.height}%`,
                      }}
                      className={`absolute rounded-[3px] border-[1.5px] border-dashed transition-all cursor-pointer ${
                        isSelected
                          ? 'border-[#0A0A0A] border-solid ring-2 ring-[#0A0A0A] ring-offset-1 bg-amber-500/20 z-30 scale-105 shadow-md'
                          : isHovered
                          ? `${config.highlightBorder} border-solid ${config.highlightBg} z-20 shadow-xs`
                          : `${config.highlightBorder} ${config.highlightBg} hover:border-solid z-10`
                      }`}
                    >
                      {/* Standard Compact CAD Circular Badge (placed top-right) */}
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

        {/* Floating Delta Tooltip upon hovering change hotspot */}
        {hoveredRegionChange && (
          <div
            className={`absolute bottom-8 left-8 z-40 p-4 rounded-[12px] shadow-lg border text-xs max-w-xs animate-in fade-in duration-150 pointer-events-none ${
              isDark
                ? 'bg-neutral-900 border-neutral-700 text-neutral-100'
                : 'bg-white border-[#E5E5E5] text-[#0A0A0A]'
            }`}
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span className="font-mono font-bold text-[11px] px-2 py-0.5 rounded-[8px] bg-[#FAFAFA] text-[#0A0A0A] border border-[#E5E5E5]">
                {hoveredRegionChange.id} ({hoveredRegionChange.zone})
              </span>
              <span className="text-[10px] text-[#A3A3A3] uppercase tracking-wider font-mono font-bold">
                {hoveredRegionChange.category.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="font-semibold text-xs mt-1 text-[#0A0A0A]">
              {hoveredRegionChange.title}
            </div>
            <div className="text-[12px] text-[#525252] mt-1 leading-normal">
              {hoveredRegionChange.description}
            </div>
            <div className="mt-2.5 pt-2 border-t border-[#E5E5E5] flex items-center justify-between text-[11px] font-mono">
              <span className="text-[#A3A3A3] line-through">Rev A: {hoveredRegionChange.oldValue}</span>
              <span className="text-[#0A0A0A] font-bold">Rev B: {hoveredRegionChange.newValue}</span>
            </div>
          </div>
        )}
      </div>

      {/* Viewport Footer Bar */}
      <div
        className={`px-4 py-2 border-t flex items-center justify-between text-[11px] font-mono ${
          isDark
            ? 'bg-neutral-900 border-neutral-800 text-neutral-400'
            : 'bg-[#FAFAFA] border-[#E5E5E5] text-[#525252]'
        }`}
      >
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 font-mono text-[11px]">
            <Crosshair className="w-3 h-3" />
            <span>
              X: {cursorPos.percentX}% | Y: {cursorPos.percentY}%
            </span>
          </span>
          <span className="font-mono text-[11px]">Zoom: {Math.round(viewportState.zoom * 100)}%</span>
        </div>

        <div className={`flex items-center gap-2 text-[13px] font-sans ${isDark ? 'text-neutral-400' : 'text-[#6b7280]'}`}>
          <span>Click drag to Pan</span>
          <span>•</span>
          <span>Scroll to Zoom</span>
        </div>
      </div>
    </div>
  );
};
