/**
 * Central design tokens for the Geometric Balance theme.
 * High-precision CAD & Engineering aesthetic:
 * - Canvas: #FAFAFA, Card Surfaces: #FFFFFF, Workspace: #F2F2F2, Near-Black: #0A0A0A
 * - Borders: #E5E5E5 crisp 1px lines, Radii: rounded-[6px]
 * - Text: #0A0A0A (Primary), #525252 (Secondary), #A3A3A3 (Muted uppercase labels)
 * - Accent: #F59E0B (Amber modifications & delta badges)
 */

export const THEME_TOKENS = {
  colors: {
    bg: {
      canvas: '#FAFAFA',
      surface: '#FFFFFF',
      workspace: '#F2F2F2',
      surfaceHover: '#FAFAFA',
      surfaceActive: '#F5F5F5',
      darkCanvas: '#0A0A0A',
      darkSurface: '#141414',
      darkSurfaceHover: '#1C1C1C',
    },
    text: {
      primary: '#0A0A0A',
      secondary: '#525252',
      muted: '#A3A3A3',
      inverted: '#FFFFFF',
    },
    border: {
      subtle: '#E5E5E5',
      medium: '#D4D4D4',
      focus: '#0A0A0A',
      dark: '#262626',
    },
    status: {
      changed: '#F59E0B',   // amber-500
      addition: '#10B981',  // emerald-500
      removal: '#EF4444',   // rose-500
      info: '#3B82F6',      // blue-500
    },
  },
  typography: {
    fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    monoFamily: 'JetBrains Mono, SF Mono, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
    scale: {
      title: 'text-[36px] sm:text-[40px] font-bold tracking-tight leading-tight',
      section: 'text-[18px] sm:text-[20px] font-semibold tracking-tight leading-snug',
      body: 'text-[14px] sm:text-[15px] leading-relaxed',
      meta: 'text-[12px] font-mono',
      label: 'text-[11px] font-bold uppercase tracking-wider',
    },
  },
  borders: {
    cardRadius: 'rounded-[12px]',
    inputRadius: 'rounded-[10px]',
    badgeRadius: 'rounded-[8px]',
    pillRadius: 'rounded-[9999px]',
    thin: 'border border-[#E5E5E5]',
    darkThin: 'border border-neutral-800',
  },
} as const;

