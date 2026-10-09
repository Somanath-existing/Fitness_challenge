import type { Tier } from '../types'
import { clsx } from 'clsx'

const TIER_CONFIG: Record<Tier, { label: string; emoji: string; classes: string }> = {
  rookie:     { label: 'Rookie',     emoji: '🌱', classes: 'bg-slate-100 text-slate-700' },
  active:     { label: 'Active',     emoji: '⚡', classes: 'bg-amber-100 text-amber-700' },
  athlete:    { label: 'Athlete',    emoji: '🏃', classes: 'bg-blue-100 text-blue-700' },
  competitor: { label: 'Competitor', emoji: '🥈', classes: 'bg-violet-100 text-violet-700' },
  elite:      { label: 'Elite',      emoji: '🏆', classes: 'bg-amber-100 text-amber-800' },
}

interface Props {
  tier: Tier
  size?: 'sm' | 'md'
}

export default function TierBadge({ tier, size = 'md' }: Props) {
  const { label, emoji, classes } = TIER_CONFIG[tier] ?? TIER_CONFIG.rookie
  return (
    <span className={clsx(
      'inline-flex items-center gap-1 rounded-full font-medium',
      size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm',
      classes,
    )}>
      {emoji} {label}
    </span>
  )
}
