import { ChevronRight } from 'lucide-react'
import type { Priority, EntityCard } from './configuration'

const priorityOptions: { value: Priority; label: string }[] = [
  { value: 'unset', label: 'Nieustawiony' },
  { value: 'essential', label: 'Core' },
  { value: 'high', label: 'Wysoki' },
  { value: 'medium', label: 'Średni' },
  { value: 'low', label: 'Niski' },
  { value: 'avoid', label: 'Odrzuć' },
]

export function EntityImage({
  entity,
  size = 'md',
}: {
  entity: EntityCard
  size?: 'sm' | 'md' | 'lg'
}) {
  const sizing =
    size === 'lg'
      ? 'h-20 w-20'
      : size === 'sm'
        ? 'h-8 w-8'
        : 'h-12 w-12'

  return (
    <div
      className={`${sizing} entity-frame relative shrink-0 overflow-hidden border border-[#66552f] bg-[#111722]`}
    >
      {entity.imageUrl ? (
        <img
          src={entity.imageUrl}
          alt=""
          className="h-full w-full object-cover"
          loading="lazy"
          onError={(event) => {
            event.currentTarget.style.display = 'none'
          }}
        />
      ) : null}
      <span className="absolute inset-0 -z-10 grid place-items-center text-xs font-black text-[#bfa65d]">
        {entity.name.slice(0, 2).toUpperCase()}
      </span>
    </div>
  )
}

export function PrioritySelect({
  value,
  onChange,
  label,
}: {
  value: Priority
  onChange: (value: Priority) => void
  label: string
}) {
  return (
    <label className="relative block min-w-32">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as Priority)}
        className="field-control h-9 w-full appearance-none rounded-sm px-3 pr-8 text-xs font-bold"
      >
        {priorityOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronRight
        aria-hidden="true"
        className="pointer-events-none absolute right-2 top-2.5 h-4 w-4 rotate-90 text-[#778398]"
      />
    </label>
  )
}

export function SectionHeading({
  icon,
  eyebrow,
  title,
  count,
}: {
  icon: React.ReactNode
  eyebrow: string
  title: string
  count: number
}) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="grid h-9 w-9 place-items-center border border-[#293445] bg-[#111721] text-[#d7b75f]">
          {icon}
        </div>
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.23em] text-[#667287]">
            {eyebrow}
          </p>
          <h2 className="font-display text-lg font-bold tracking-wide text-[#edf2f7]">
            {title}
          </h2>
        </div>
      </div>
      <span className="rounded-sm border border-[#273243] bg-[#0d121b] px-2 py-1 font-mono text-[10px] text-[#7f8b9d]">
        {String(count).padStart(2, '0')}
      </span>
    </div>
  )
}

export function WeightControl({
  label,
  value,
  color,
  onChange,
}: {
  label: string
  value: number
  color: string
  onChange: (value: number) => void
}) {
  return (
    <label className="block">
      <span className="mb-2 flex items-baseline justify-between text-xs font-bold text-[#aeb8c7]">
        {label}
        <span className="font-mono text-sm text-[#f2d37c]">{value}%</span>
      </span>
      <input
        type="range"
        min="0"
        max="100"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="weight-range w-full"
        style={{ '--track-color': color } as React.CSSProperties}
      />
    </label>
  )
}
