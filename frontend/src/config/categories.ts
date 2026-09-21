import { ChangeCategory } from '../types/comparison';

export interface CategoryMeta {
  key: ChangeCategory;
  label: string;
  shortLabel: string;
  description: string;
  badgeBg: string;
  badgeBorder: string;
  badgeText: string;
  highlightBorder: string;
  highlightBg: string;
  iconName: 'Ruler' | 'FileText' | 'PlusCircle' | 'MinusCircle' | 'Tag' | 'Sliders';
  dotColor: string;
}

/**
 * Central configuration for engineering change categories.
 * Adding a new category here automatically flows through the badges, filters,
 * diff highlight layers, and report tables.
 */
export const CATEGORY_CONFIG: Record<ChangeCategory, CategoryMeta> = {
  dimension_change: {
    key: 'dimension_change',
    label: 'Dimension Change',
    shortLabel: 'Dimension',
    description: 'Modifications to linear, angular, or radial dimensions.',
    badgeBg: 'bg-neutral-100',
    badgeBorder: 'border-neutral-300',
    badgeText: 'text-neutral-900',
    highlightBorder: 'border-amber-500',
    highlightBg: 'bg-amber-500/15',
    iconName: 'Ruler',
    dotColor: 'bg-amber-500',
  },
  note_change: {
    key: 'note_change',
    label: 'Note / Annotation',
    shortLabel: 'Note',
    description: 'Updated general notes, callouts, or revision text blocks.',
    badgeBg: 'bg-neutral-100',
    badgeBorder: 'border-neutral-300',
    badgeText: 'text-neutral-900',
    highlightBorder: 'border-blue-500',
    highlightBg: 'bg-blue-500/15',
    iconName: 'FileText',
    dotColor: 'bg-blue-500',
  },
  addition: {
    key: 'addition',
    label: 'New Feature (Added)',
    shortLabel: 'Added',
    description: 'Geometry, holes, ports, or components introduced in the new revision.',
    badgeBg: 'bg-emerald-50 text-emerald-950',
    badgeBorder: 'border-emerald-300',
    badgeText: 'text-emerald-900',
    highlightBorder: 'border-emerald-500',
    highlightBg: 'bg-emerald-500/15',
    iconName: 'PlusCircle',
    dotColor: 'bg-emerald-500',
  },
  removal: {
    key: 'removal',
    label: 'Removed Feature',
    shortLabel: 'Removed',
    description: 'Elements present in baseline drawing that were deleted in current revision.',
    badgeBg: 'bg-rose-50 text-rose-950',
    badgeBorder: 'border-rose-300',
    badgeText: 'text-rose-900',
    highlightBorder: 'border-rose-500',
    highlightBg: 'bg-rose-500/15',
    iconName: 'MinusCircle',
    dotColor: 'bg-rose-500',
  },
  symbol_change: {
    key: 'symbol_change',
    label: 'Symbol & Callout',
    shortLabel: 'Symbol',
    description: 'Changes in welding, surface finish, GD&T symbols, or electrical tags.',
    badgeBg: 'bg-neutral-100',
    badgeBorder: 'border-neutral-300',
    badgeText: 'text-neutral-900',
    highlightBorder: 'border-purple-500',
    highlightBg: 'bg-purple-500/15',
    iconName: 'Tag',
    dotColor: 'bg-purple-500',
  },
  tolerance_change: {
    key: 'tolerance_change',
    label: 'Tolerance & Fit',
    shortLabel: 'Tolerance',
    description: 'Modifications to bilateral, geometric, or limit tolerances.',
    badgeBg: 'bg-neutral-100',
    badgeBorder: 'border-neutral-300',
    badgeText: 'text-neutral-900',
    highlightBorder: 'border-orange-500',
    highlightBg: 'bg-orange-500/15',
    iconName: 'Sliders',
    dotColor: 'bg-orange-500',
  },
  // Backend-native category keys (sent by /api/compare and drawing compares).
  // Kept in sync with the backend CATEGORY_COLORS mapping.
  note_or_annotation_change: {
    key: 'note_or_annotation_change',
    label: 'Note / Annotation',
    shortLabel: 'Note',
    description: 'Updated general notes, callouts, or revision text blocks.',
    badgeBg: 'bg-neutral-100',
    badgeBorder: 'border-neutral-300',
    badgeText: 'text-neutral-900',
    highlightBorder: 'border-blue-500',
    highlightBg: 'bg-blue-500/15',
    iconName: 'FileText',
    dotColor: 'bg-blue-500',
  },
  symbol_or_code_change: {
    key: 'symbol_or_code_change',
    label: 'Symbol & Callout',
    shortLabel: 'Symbol',
    description: 'Changes in welding, surface finish, GD&T symbols, or electrical tags.',
    badgeBg: 'bg-neutral-100',
    badgeBorder: 'border-neutral-300',
    badgeText: 'text-neutral-900',
    highlightBorder: 'border-purple-500',
    highlightBg: 'bg-purple-500/15',
    iconName: 'Tag',
    dotColor: 'bg-purple-500',
  },
  needs_human_review: {
    key: 'needs_human_review',
    label: 'Needs Human Review',
    shortLabel: 'Review',
    description: 'OCR and model evidence disagree — requires a human decision.',
    badgeBg: 'bg-amber-50 text-amber-950',
    badgeBorder: 'border-amber-300',
    badgeText: 'text-amber-900',
    highlightBorder: 'border-amber-500',
    highlightBg: 'bg-amber-500/15',
    iconName: 'Sliders',
    dotColor: 'bg-amber-500',
  },

  // ── Hybrid VLM pipeline categories (Track A + Track B) ────────────────────
  geometry_change: {
    key: 'geometry_change',
    label: 'Geometry Change',
    shortLabel: 'Geometry',
    description: 'Visual/geometric change detected without a labeled dimension (Track B).',
    badgeBg: 'bg-cyan-50',
    badgeBorder: 'border-cyan-400',
    badgeText: 'text-cyan-900',
    highlightBorder: 'border-cyan-500',
    highlightBg: 'bg-cyan-500/15',
    iconName: 'Sliders',
    dotColor: 'bg-cyan-500',
  },
  reconfiguration: {
    key: 'reconfiguration',
    label: 'Reconfiguration',
    shortLabel: 'Reconfig',
    description: 'Layout or configuration of components has been rearranged.',
    badgeBg: 'bg-violet-50',
    badgeBorder: 'border-violet-400',
    badgeText: 'text-violet-900',
    highlightBorder: 'border-violet-500',
    highlightBg: 'bg-violet-500/15',
    iconName: 'Sliders',
    dotColor: 'bg-violet-500',
  },
  relabel: {
    key: 'relabel',
    label: 'Relabel',
    shortLabel: 'Relabel',
    description: 'Text label or name was changed without a numeric value change.',
    badgeBg: 'bg-sky-50',
    badgeBorder: 'border-sky-400',
    badgeText: 'text-sky-900',
    highlightBorder: 'border-sky-500',
    highlightBg: 'bg-sky-500/15',
    iconName: 'Tag',
    dotColor: 'bg-sky-500',
  },
  layout_change: {
    key: 'layout_change',
    label: 'Layout Change',
    shortLabel: 'Layout',
    description: 'Floor plan layout, room arrangement, or spatial organization has changed.',
    badgeBg: 'bg-indigo-50',
    badgeBorder: 'border-indigo-400',
    badgeText: 'text-indigo-900',
    highlightBorder: 'border-indigo-500',
    highlightBg: 'bg-indigo-500/15',
    iconName: 'FileText',
    dotColor: 'bg-indigo-500',
  },
  structural_change: {
    key: 'structural_change',
    label: 'Structural Change',
    shortLabel: 'Structural',
    description: 'Walls, openings, columns, or structural elements changed (Track B).',
    badgeBg: 'bg-orange-50',
    badgeBorder: 'border-orange-400',
    badgeText: 'text-orange-900',
    highlightBorder: 'border-orange-500',
    highlightBg: 'bg-orange-500/15',
    iconName: 'Sliders',
    dotColor: 'bg-orange-500',
  },
  fixture_change: {
    key: 'fixture_change',
    label: 'Fixture Change',
    shortLabel: 'Fixture',
    description: 'Fixture, fitting, or installed component was moved, added, or removed.',
    badgeBg: 'bg-teal-50',
    badgeBorder: 'border-teal-400',
    badgeText: 'text-teal-900',
    highlightBorder: 'border-teal-500',
    highlightBg: 'bg-teal-500/15',
    iconName: 'PlusCircle',
    dotColor: 'bg-teal-500',
  },
  title_block_change: {
    key: 'title_block_change',
    label: 'Title Block',
    shortLabel: 'Title Block',
    description: 'Change in the title block (sheet number, revision, date, project name).',
    badgeBg: 'bg-neutral-100',
    badgeBorder: 'border-neutral-400',
    badgeText: 'text-neutral-900',
    highlightBorder: 'border-neutral-500',
    highlightBg: 'bg-neutral-500/15',
    iconName: 'FileText',
    dotColor: 'bg-neutral-500',
  },
  other: {
    key: 'other',
    label: 'Other Change',
    shortLabel: 'Other',
    description: 'Change that does not fit a specific category.',
    badgeBg: 'bg-slate-50',
    badgeBorder: 'border-slate-400',
    badgeText: 'text-slate-900',
    highlightBorder: 'border-slate-500',
    highlightBg: 'bg-slate-500/15',
    iconName: 'FileText',
    dotColor: 'bg-slate-500',
  },
};

export function getCategoryConfig(category: ChangeCategory | string): CategoryMeta {
  if (category in CATEGORY_CONFIG) {
    return CATEGORY_CONFIG[category as ChangeCategory];
  }
  // Fallback for unknown categories
  return {
    key: 'dimension_change',
    label: String(category).replace(/_/g, ' '),
    shortLabel: String(category).replace(/_/g, ' '),
    description: 'Uncategorized revision change.',
    badgeBg: 'bg-neutral-100',
    badgeBorder: 'border-neutral-300',
    badgeText: 'text-neutral-800',
    highlightBorder: 'border-neutral-500',
    highlightBg: 'bg-neutral-500/15',
    iconName: 'FileText',
    dotColor: 'bg-neutral-500',
  };
}

export const ALL_CATEGORIES = Object.keys(CATEGORY_CONFIG) as ChangeCategory[];
