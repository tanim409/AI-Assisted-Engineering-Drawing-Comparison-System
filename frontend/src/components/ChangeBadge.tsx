import React from 'react';
import { ChangeCategory } from '../types/comparison';
import { getCategoryConfig } from '../config/categories';
import { Ruler, FileText, PlusCircle, MinusCircle, Tag, Sliders } from 'lucide-react';

interface ChangeBadgeProps {
  category: ChangeCategory | string;
  size?: 'sm' | 'md';
  showIcon?: boolean;
  showDot?: boolean;
}

const ICON_MAP = {
  Ruler,
  FileText,
  PlusCircle,
  MinusCircle,
  Tag,
  Sliders,
};

export const ChangeBadge: React.FC<ChangeBadgeProps> = ({
  category,
  size = 'md',
  showIcon = true,
  showDot = false,
}) => {
  const config = getCategoryConfig(category);
  const IconComponent = ICON_MAP[config.iconName] || FileText;

  const sizeClasses =
    size === 'sm'
      ? 'px-2 py-0.5 text-xs gap-1 font-medium'
      : 'px-2.5 py-1 text-xs gap-1.5 font-medium';

  return (
    <span
      id={`badge-cat-${config.key}`}
      className={`inline-flex items-center select-none rounded-[8px] border font-mono tracking-tight whitespace-nowrap ${config.badgeBg} ${config.badgeBorder} ${config.badgeText} ${sizeClasses}`}
      title={config.description}
    >
      {showDot && (
        <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor} shrink-0`} />
      )}
      {showIcon && <IconComponent className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />}
      <span>{config.label}</span>
    </span>
  );
};
