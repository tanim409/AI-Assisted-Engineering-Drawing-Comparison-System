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
