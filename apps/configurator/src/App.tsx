import {
  Boxes,
  Check,
  CheckCheck,
  ChevronRight,
  CircleAlert,
  CircleDot,
  ExternalLink,
  LoaderCircle,
  RotateCcw,
  Save,
  Search,
  SlidersHorizontal,
  Sparkles,
  Sword,
  UsersRound,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

type Priority =
  | 'unset'
  | 'essential'
  | 'high'
  | 'medium'
  | 'low'
  | 'avoid'
type ConfigurationStatus = 'draft' | 'ready'

type EntityCard = {
  apiName: string
  name: string
  imageUrl: string | null
  type?: string | null
}

type UnitCard = EntityCard & {
  boardIndex: number | null
  stars: number | null
  items: EntityCard[]
}

type ComponentCard = EntityCard & {
  requiredCount: number
}

type ItemRecommendation = EntityCard & {
  components: EntityCard[]
}

type AugmentCard = EntityCard & {
  disabledAtSource: boolean
}

type PriorityDecision = {
  apiName: string
  priority: Priority
}

type UnitPriorityDecision = PriorityDecision & { core: boolean }

type Configuration = {
  schemaVersion: 1
  sourceId: string
  setNumber: number
  status: ConfigurationStatus
  weights: {
    units: number
    components: number
    augments: number
  }
  units: UnitPriorityDecision[]
  components: PriorityDecision[]
  augments: PriorityDecision[]
  notes: string
  updatedAt: string | null
}

type CompositionSummary = {
  sourceId: string
  title: string
  slug: string
  position: number
  configured: boolean
}

type CompositionWorkspace = {
  source: {
    sourceId: string
    title: string
    metaTitle: string | null
    slug: string
    set: number
    tier: string | null
    style: string | null
    difficulty: string | null
    updatedAt: string | null
    mainChampion: EntityCard | null
    augmentTip: string | null
    tips: { stage: string; tip: string }[]
  }
  finalUnits: UnitCard[]
  earlyUnits: UnitCard[]
  itemRecommendations: ItemRecommendation[]
  components: ComponentCard[]
  augments: AugmentCard[]
  configuration: Configuration
}

const priorityOptions: { value: Priority; label: string }[] = [
  { value: 'unset', label: 'Nieustawiony' },
  { value: 'essential', label: 'Core' },
  { value: 'high', label: 'Wysoki' },
  { value: 'medium', label: 'Średni' },
  { value: 'low', label: 'Niski' },
  { value: 'avoid', label: 'Odrzuć' },
]

function messageFromResponse(payload: unknown): string {
  if (
    typeof payload === 'object' &&
    payload !== null &&
    'detail' in payload
  ) {
    const detail = payload.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((entry) =>
          typeof entry === 'object' &&
          entry !== null &&
          'msg' in entry
            ? String(entry.msg)
            : 'Nieprawidłowa wartość',
        )
        .join(', ')
    }
  }
  return 'Wystąpił nieoczekiwany błąd'
}

async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  const payload = (await response.json()) as unknown
  if (!response.ok) throw new Error(messageFromResponse(payload))
  return payload as T
}

async function loadWorkspace(url: string, init?: RequestInit): Promise<CompositionWorkspace> {
  const workspace = await readJson<CompositionWorkspace>(url, init)
  return { ...workspace, configuration: withUnitDefaults(workspace.configuration, workspace.earlyUnits) }
}

function withUnitDefaults(configuration: Configuration, earlyUnits: UnitCard[]): Configuration {
  return {
    ...configuration,
    units: (configuration.units ?? Array.from(new Set(earlyUnits.map((unit) => unit.apiName)), (apiName) => ({ apiName, priority: 'medium' as const, core: false }))).map((unit) => ({ ...unit, core: unit.core ?? false })),
  }
}

function EntityImage({
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

function PrioritySelect({
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

function SectionHeading({
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

function WeightControl({
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

function App({ active = true }: { active?: boolean }) {
  const [compositions, setCompositions] = useState<CompositionSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [workspace, setWorkspace] = useState<CompositionWorkspace | null>(null)
  const [configuration, setConfiguration] = useState<Configuration | null>(null)
  const [baseline, setBaseline] = useState<Configuration | null>(null)
  const [query, setQuery] = useState('')
  const [loadingList, setLoadingList] = useState(true)
  const [loadingWorkspace, setLoadingWorkspace] = useState(true)
  const [saving, setSaving] = useState(false)
  const [bootstrapping, setBootstrapping] = useState(false)
  const [notice, setNotice] = useState<{ tone: 'ok' | 'error'; text: string } | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    readJson<{ compositions: CompositionSummary[] }>('/api/compositions', {
      signal: controller.signal,
    })
      .then(({ compositions: entries }) => {
        setCompositions(entries)
        setSelectedId((current) => current ?? entries[0]?.sourceId ?? null)
      })
      .catch((error: unknown) => {
        if ((error as Error).name !== 'AbortError') {
          setNotice({ tone: 'error', text: (error as Error).message })
        }
      })
      .finally(() => setLoadingList(false))
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!selectedId) return
    const controller = new AbortController()
    loadWorkspace(`/api/compositions/${selectedId}`, {
      signal: controller.signal,
    })
      .then((nextWorkspace) => {
        setWorkspace(nextWorkspace)
        setConfiguration(nextWorkspace.configuration)
        setBaseline(nextWorkspace.configuration)
      })
      .catch((error: unknown) => {
        if ((error as Error).name !== 'AbortError') {
          setNotice({ tone: 'error', text: (error as Error).message })
        }
      })
      .finally(() => setLoadingWorkspace(false))
    return () => controller.abort()
  }, [selectedId])

  const dirty =
    configuration !== null &&
    baseline !== null &&
    JSON.stringify(configuration) !== JSON.stringify(baseline)

  const configuredCount = useMemo(
    () => compositions.filter((composition) => composition.configured).length,
    [compositions],
  )

  const filteredCompositions = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase('pl')
    if (!needle) return compositions
    return compositions.filter((composition) =>
      composition.title.toLocaleLowerCase('pl').includes(needle),
    )
  }, [compositions, query])

  const progress = useMemo(() => {
    if (!configuration) return { done: 0, total: 0, percent: 0 }
    const priorities = [
      ...configuration.components,
      ...configuration.augments,
    ]
    const done = priorities.filter(
      (decision) => decision.priority !== 'unset',
    ).length
    const total = priorities.length
    return {
      done,
      total,
      percent: total ? Math.round((done / total) * 100) : 100,
    }
  }, [configuration])

  const weightTotal = configuration
    ? Object.values(configuration.weights).reduce(
        (sum, value) => sum + value,
        0,
      )
    : 0

  const selectComposition = (sourceId: string) => {
    if (
      dirty &&
      !window.confirm('Masz niezapisane zmiany. Przejść dalej i je odrzucić?')
    ) {
      return
    }
    setLoadingWorkspace(true)
    setSelectedId(sourceId)
  }

  const changeComponentPriority = (
    apiName: string,
    priority: Priority,
  ) => {
    setConfiguration((current) =>
      current
        ? {
            ...current,
            components: current.components.map((decision) =>
              decision.apiName === apiName
                ? { ...decision, priority }
                : decision,
            ),
          }
        : current,
    )
  }

  const changeUnitCore = (apiName: string, core: boolean) => {
    setConfiguration((current) => current ? {
      ...current,
      units: current.units.map((decision) => decision.apiName === apiName ? { ...decision, core } : decision),
    } : current)
  }

  const changeAugment = (apiName: string, priority: Priority) => {
    if (priority === 'essential' && configuration?.augments.some((decision) => decision.apiName !== apiName && decision.priority === 'essential')) {
      setNotice({ tone: 'error', text: 'Kompozycja moze miec tylko jeden augment Core.' })
      return
    }
    setConfiguration((current) =>
      current
        ? {
            ...current,
            augments: current.augments.map((decision) =>
              decision.apiName === apiName
                ? { ...decision, priority }
                : decision,
            ),
          }
        : current,
    )
  }

  const changeWeight = (
    key: keyof Configuration['weights'],
    value: number,
  ) => {
    setConfiguration((current) =>
      current
        ? {
            ...current,
            weights: { ...current.weights, [key]: value },
          }
        : current,
    )
  }

  const save = async () => {
    if (!configuration || !selectedId) {
      return {
        saved: false as const,
        error: 'Nie wybrano kompozycji do zapisania.',
      }
    }
    if (weightTotal !== 100) {
      const error = 'Wagi muszą sumować się dokładnie do 100%.'
      setNotice({
        tone: 'error',
        text: error,
      })
      return { saved: false as const, error }
    }

    setSaving(true)
    setNotice(null)
    try {
      const result = await readJson<{ configuration: Configuration }>(
        `/api/compositions/${selectedId}/configuration`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(configuration),
        },
      )
      const saved = withUnitDefaults(result.configuration, workspace?.earlyUnits ?? [])
      setConfiguration(saved)
      setBaseline(saved)
      setCompositions((current) =>
        current.map((composition) =>
          composition.sourceId === selectedId
            ? { ...composition, configured: true }
            : composition,
        ),
      )
      setNotice({
        tone: 'ok',
        text: 'Zapisano konfigurację w data/curated.',
      })
      return {
        saved: true as const,
        sourceId: selectedId,
        status: result.configuration.status,
      }
    } catch (error) {
      const message = (error as Error).message
      setNotice({ tone: 'error', text: message })
      return { saved: false as const, error: message }
    } finally {
      setSaving(false)
    }
  }

  const bootstrapAll = async () => {
    if (dirty) {
      setNotice({
        tone: 'error',
        text: 'Najpierw zapisz albo cofnij zmiany bieżącej kompozycji.',
      })
      return
    }

    const confirmed = window.confirm(
      `Zapisać wszystkie ${compositions.length} kompozycji jako ready w data/curated?\n\nIstniejące ręczne priorytety zostaną zachowane.`,
    )
    if (!confirmed) return

    setBootstrapping(true)
    setNotice(null)
    try {
      const result = await readJson<{
        saved: number
        sourceIds: string[]
      }>('/api/compositions/bootstrap-ready', { method: 'POST' })

      setCompositions((current) =>
        current.map((composition) =>
          result.sourceIds.includes(composition.sourceId)
            ? { ...composition, configured: true }
            : composition,
        ),
      )

      if (selectedId && result.sourceIds.includes(selectedId)) {
        const nextWorkspace = await loadWorkspace(
          `/api/compositions/${selectedId}`,
        )
        setWorkspace(nextWorkspace)
        setConfiguration(nextWorkspace.configuration)
        setBaseline(nextWorkspace.configuration)
      }

      setNotice({
        tone: 'ok',
        text: `Zapisano ${result.saved} kompozycji jako gotowe dla silnika.`,
      })
    } catch (error) {
      setNotice({ tone: 'error', text: (error as Error).message })
    } finally {
      setBootstrapping(false)
    }
  }

  const saveToolRef = useRef<typeof save | null>(null)
  useEffect(() => {
    saveToolRef.current = save
  })

  useEffect(() => {
    if (!active) return
    const context = document.modelContext
    if (!context?.registerTool) return

    const lifecycle = new AbortController()
    void Promise.resolve(
      context.registerTool(
        {
          name: 'save_current_composition_configuration',
          title: 'Zapisz konfigurację kompozycji',
          description:
            'Zapisuje aktualnie widoczne decyzje konfiguratora jako curated JSON.',
          inputSchema: {
            type: 'object',
            properties: {},
            additionalProperties: false,
          },
          annotations: {
            readOnlyHint: false,
            untrustedContentHint: false,
          },
          async execute() {
            const saveCurrent = saveToolRef.current
            if (!saveCurrent) throw new Error("Save action is not ready")
            const result = await saveCurrent()
            if (!result.saved) throw new Error(result.error)
            return result
          },
        },
        { signal: lifecycle.signal },
      ),
    ).catch((error: unknown) => {
      console.error('Could not register WebMCP save tool', error)
    })

    return () => lifecycle.abort()
  }, [active])

  return (
    <div className="min-h-screen bg-[#080b11] text-[#aeb8c7]">
      <header className="sticky top-16 z-30 border-b border-[#252d3a] bg-[#0a0e15]/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1720px] items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="logo-mark grid h-9 w-9 place-items-center border border-[#836d36] bg-[#17170f] text-[#f1cd68]">
              <Sword className="h-5 w-5" />
            </div>
            <div>
              <p className="font-display text-sm font-black tracking-[0.16em] text-[#f1f4f8]">
                TFT SPOT
              </p>
              <p className="text-[9px] font-bold uppercase tracking-[0.25em] text-[#647186]">
                Composition Lab
              </p>
            </div>
          </div>

          <div className="hidden items-center gap-5 sm:flex">
            <div className="text-right">
              <p className="text-[9px] font-black uppercase tracking-[0.18em] text-[#5d697b]">
                Postęp kompozycji
              </p>
              <p className="font-mono text-xs text-[#dce3ec]">
                {progress.done}/{progress.total} pól · {progress.percent}%
              </p>
            </div>
            <div className="h-7 w-px bg-[#273141]" />
            <span
              className={`flex items-center gap-2 text-xs font-bold ${
                dirty ? 'text-[#efc967]' : 'text-[#6d7a8c]'
              }`}
            >
              <CircleDot className="h-3.5 w-3.5" />
              {dirty ? 'Niezapisane zmiany' : 'Stan zapisany'}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1720px] gap-0 lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="border-b border-[#252d3a] bg-[#0c1018] lg:sticky lg:top-16 lg:h-[calc(100vh-4rem)] lg:border-b-0 lg:border-r">
          <div className="border-b border-[#232c39] p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-[#687487]">
                  Snapshot
                </p>
                <h2 className="font-display text-lg font-bold text-[#edf1f7]">
                  Set 18
                </h2>
              </div>
              <span className="border border-[#343e4e] bg-[#111721] px-2 py-1 font-mono text-[10px] text-[#94a0b2]">
                {compositions.length} COMPS
              </span>
            </div>
            <label className="relative block">
              <span className="sr-only">Szukaj kompozycji</span>
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#536076]" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Szukaj kompozycji…"
                className="field-control h-9 w-full rounded-sm pl-9 pr-3 text-xs outline-none"
              />
            </label>

            <div className="mt-4 border border-[#3a3828] bg-[#12140f] p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-[0.16em] text-[#8f7b45]">
                  Curated bootstrap
                </span>
                <span className="font-mono text-[10px] text-[#b9a15d]">
                  {configuredCount}/{compositions.length}
                </span>
              </div>
              <button
                type="button"
                onClick={bootstrapAll}
                disabled={
                  loadingList ||
                  bootstrapping ||
                  dirty ||
                  compositions.length === 0
                }
                className="primary-button w-full"
              >
                {bootstrapping ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCheck className="h-4 w-4" />
                )}
                {bootstrapping ? 'Zapisuję…' : 'Wszystkie jako ready'}
              </button>
              <p className="mt-2 text-[10px] leading-4 text-[#6f786b]">
                {dirty
                  ? 'Najpierw zapisz albo cofnij bieżące zmiany.'
                  : 'Komponenty: Core · augmenty: medium'}
              </p>
            </div>
          </div>

          <nav
            aria-label="Kompozycje"
            className="max-h-72 overflow-y-auto p-2 lg:max-h-[calc(100vh-17.5rem)]"
          >
            {loadingList ? (
              <div className="grid h-32 place-items-center text-[#758196]">
                <LoaderCircle className="h-5 w-5 animate-spin" />
              </div>
            ) : (
              filteredCompositions.map((composition) => {
                const active = composition.sourceId === selectedId
                return (
                  <button
                    key={composition.sourceId}
                    type="button"
                    onClick={() => selectComposition(composition.sourceId)}
                    className={`group mb-1 flex w-full items-center gap-3 border px-3 py-2.5 text-left transition ${
                      active
                        ? 'border-[#73602e] bg-[#1a1912] text-[#f1d27a]'
                        : 'border-transparent text-[#8d98aa] hover:border-[#273243] hover:bg-[#111721] hover:text-[#dce3ec]'
                    }`}
                  >
                    <span
                      className={`grid h-7 w-7 shrink-0 place-items-center font-mono text-[10px] ${
                        active
                          ? 'bg-[#d2ae51] text-[#111008]'
                          : 'bg-[#151b25] text-[#647087]'
                      }`}
                    >
                      {String(composition.position + 1).padStart(2, '0')}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-bold">
                        {composition.title}
                      </span>
                      <span className="mt-0.5 block truncate font-mono text-[9px] uppercase text-[#536075]">
                        {composition.slug.replace('set-18-', '')}
                      </span>
                    </span>
                    {composition.configured ? (
                      <Check className="h-3.5 w-3.5 text-[#5fbb94]" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 opacity-40 group-hover:opacity-100" />
                    )}
                  </button>
                )
              })
            )}
          </nav>
        </aside>

        <section className="min-w-0">
          {loadingWorkspace || !workspace || !configuration ? (
            <div className="grid min-h-[calc(100vh-4rem)] place-items-center">
              <div className="text-center">
                <LoaderCircle className="mx-auto mb-3 h-7 w-7 animate-spin text-[#d2ae51]" />
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#667287]">
                  Ładuję raw composition
                </p>
              </div>
            </div>
          ) : (
            <>
              <div className="border-b border-[#252e3c] bg-[#0d121a] px-4 py-6 sm:px-7">
                <div className="flex flex-col justify-between gap-6 xl:flex-row xl:items-center">
                  <div className="flex min-w-0 items-center gap-4">
                    {workspace.source.mainChampion ? (
                      <EntityImage entity={workspace.source.mainChampion} size="lg" />
                    ) : null}
                    <div className="min-w-0">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className="tier-badge bg-[#9c743b] text-[#fff1c8]">
                          TIER {workspace.source.tier || '—'}
                        </span>
                        <span className="meta-badge">
                          {workspace.source.style || 'Bez stylu'}
                        </span>
                        <span className="meta-badge">
                          {workspace.source.difficulty || '—'}
                        </span>
                      </div>
                      <h1 className="font-display text-2xl font-black tracking-wide text-[#f4f6fa] sm:text-3xl">
                        {workspace.source.title}
                      </h1>
                      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[#69768a]">
                        <span>Set {workspace.source.set}</span>
                        <span>Source {workspace.source.sourceId}</span>
                        <a
                          href={`https://tftacademy.com/tierlist/comps/${workspace.source.slug}`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-[#aa9254] hover:text-[#e3c46f]"
                        >
                          TFT Academy <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        if (baseline) setConfiguration(baseline)
                      }}
                      disabled={!dirty}
                      className="secondary-button"
                    >
                      <RotateCcw className="h-4 w-4" />
                      Cofnij
                    </button>
                    <button
                      type="button"
                      onClick={save}
                      disabled={!dirty || saving || weightTotal !== 100}
                      className="primary-button"
                    >
                      {saving ? (
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                      ) : (
                        <Save className="h-4 w-4" />
                      )}
                      Zapisz konfigurację
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-4 pb-0 sm:p-7 sm:pb-0">
                <section className="panel-cut border border-[#343527] bg-[#12140f] p-4 sm:p-5">
                  <SectionHeading
                    icon={<Sword className="h-4 w-4" />}
                    eyebrow="Reference board"
                    title="Final composition"
                    count={workspace.finalUnits.length}
                  />
                  <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
                    {workspace.finalUnits.map((unit) => (
                      <article
                        key={unit.apiName}
                        className="border border-[#303529] bg-[#0b100d] p-3"
                      >
                        <div className="mb-3 flex items-start gap-3">
                          <EntityImage entity={unit} />
                          <div className="min-w-0 flex-1">
                            <h3 className="truncate text-sm font-black text-[#e8edf4]">
                              {unit.name}
                            </h3>
                            <p className="mt-1 font-mono text-[9px] text-[#6f765e]">
                              HEX {unit.boardIndex ?? '—'} · {unit.stars ?? 1}★
                            </p>
                          </div>
                        </div>
                        <div className="flex min-h-8 gap-1.5">
                          {unit.items.length ? (
                            unit.items.map((item, index) => (
                              <div
                                key={`${item.apiName}-${index}`}
                                title={item.name}
                              >
                                <EntityImage entity={item} size="sm" />
                              </div>
                            ))
                          ) : (
                            <span className="self-center text-[10px] text-[#555d50]">
                              Brak itemów
                            </span>
                          )}
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              </div>

              <div className="grid gap-5 p-4 sm:p-7 2xl:grid-cols-[minmax(0,1fr)_320px]">
                <div className="space-y-5">
                  <section className="panel-cut border border-[#252f3e] bg-[#0e141d] p-4 sm:p-5">
                    <SectionHeading
                      icon={<UsersRound className="h-4 w-4" />}
                      eyebrow="Sygnał 01"
                      title="Early units"
                      count={workspace.earlyUnits.length}
                    />
                    <p className="mb-3 text-xs text-[#8f9bad]">Core odpowiada za 75% oceny jednostek przy jednym core, 87,5% przy dwóch i więcej przy kolejnych. Sygnał rośnie do 4 kopii.</p>
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      {workspace.earlyUnits.map((unit) => (
                        <article
                          key={unit.apiName}
                          className="border border-[#252f3e] bg-[#0b1018] p-3 transition hover:border-[#4d4833]"
                        >
                          <div className="mb-3 flex items-start gap-3">
                            <EntityImage entity={unit} />
                            <div className="min-w-0 flex-1">
                              <h3 className="truncate text-sm font-black text-[#e8edf4]">
                                {unit.name}
                              </h3>
                              <p className="mt-1 font-mono text-[9px] text-[#566277]">
                                EARLY · {unit.stars ?? 1}★
                              </p>
                            </div>
                          </div>
                          <div className="flex min-h-8 gap-1.5">
                            {unit.items.length ? (
                              unit.items.map((item, index) => (
                                <div
                                  key={`${item.apiName}-${index}`}
                                  title={item.name}
                                >
                                  <EntityImage entity={item} size="sm" />
                                </div>
                              ))
                            ) : (
                              <span className="self-center text-[10px] text-[#4f5a6c]">
                                Brak itemów w openerze
                              </span>
                            )}
                          </div>
                          <label className="mt-3 flex items-center gap-2 text-xs text-[#b7c4d6]">
                            <input type="checkbox" className="h-4 w-4 accent-[#d2ae51]"
                              aria-label={`Core jednostka ${unit.name}`}
                              checked={configuration.units.find((decision) => decision.apiName === unit.apiName)?.core ?? false}
                              onChange={(event) => changeUnitCore(unit.apiName, event.target.checked)} />
                            Core jednostka
                          </label>
                        </article>
                      ))}
                    </div>
                  </section>

                  <section className="panel-cut border border-[#252f3e] bg-[#0e141d] p-4 sm:p-5">
                    <SectionHeading
                      icon={<Sparkles className="h-4 w-4" />}
                      eyebrow="Sygnał 02"
                      title="Augmenty"
                      count={workspace.augments.length}
                    />
                    <p className="mb-3 text-xs text-[#8f9bad]">Core wymaga wyboru tego augmentu. Maksymalnie jeden na kompozycje.</p>
                    <div className="overflow-hidden border border-[#242e3c]">
                      <div className="hidden grid-cols-[minmax(0,1fr)_170px] gap-4 border-b border-[#242e3c] bg-[#111822] px-4 py-2 text-[9px] font-black uppercase tracking-[0.18em] text-[#5f6b7d] md:grid">
                        <span>Augment</span>
                        <span>Priorytet</span>
                      </div>
                      {workspace.augments.map((augment) => {
                        const decision = configuration.augments.find(
                          (entry) => entry.apiName === augment.apiName,
                        )
                        return (
                          <article
                            key={augment.apiName}
                            className="grid gap-3 border-b border-[#222b38] bg-[#0b1018] p-3 last:border-b-0 md:grid-cols-[minmax(0,1fr)_170px] md:items-center md:gap-4 md:px-4"
                          >
                            <div className="flex min-w-0 items-center gap-3">
                              <EntityImage entity={augment} />
                              <div className="min-w-0">
                                <h3 className="truncate text-sm font-black text-[#e5eaf1]">
                                  {augment.name}
                                </h3>
                                <p className="truncate font-mono text-[9px] text-[#556176]">
                                  {augment.apiName}
                                </p>
                              </div>
                            </div>
                            <PrioritySelect
                              label={`Priorytet augmentu ${augment.name}`}
                              value={decision?.priority ?? 'unset'}
                              onChange={(priority) =>
                                changeAugment(augment.apiName, priority)
                              }
                            />
                          </article>
                        )
                      })}
                    </div>
                  </section>

                  <section className="panel-cut border border-[#252f3e] bg-[#0e141d] p-4 sm:p-5">
                    <SectionHeading
                      icon={<Boxes className="h-4 w-4" />}
                      eyebrow="Sygnał 03"
                      title="Itemy i komponenty"
                      count={workspace.itemRecommendations.length}
                    />

                    <div className="mb-3 flex items-center justify-between">
                      <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#667287]">
                        Polecana linia z Academy
                      </p>
                      <span className="font-mono text-[9px] text-[#536075]">
                        ITEM → RECEPTURA
                      </span>
                    </div>
                    <div className="mb-5 grid gap-2 md:grid-cols-2">
                      {workspace.itemRecommendations.map((item) => (
                        <article
                          key={item.apiName}
                          className="flex min-w-0 items-center gap-3 border border-[#252f3e] bg-[#0b1018] p-3"
                        >
                          <EntityImage entity={item} />
                          <div className="min-w-0 flex-1">
                            <h3 className="truncate text-xs font-black text-[#e3e8ef]">
                              {item.name}
                            </h3>
                            <p className="mt-1 font-mono text-[9px] uppercase text-[#556176]">
                              {item.type === 'components'
                                ? 'Direct component'
                                : 'Recommended item'}
                            </p>
                          </div>
                          {item.components.length ? (
                            <>
                              <ChevronRight className="h-4 w-4 shrink-0 text-[#75643a]" />
                              <div className="flex shrink-0 gap-1.5">
                                {item.components.map((component, index) => (
                                  <div
                                    key={`${component.apiName}-${index}`}
                                    title={component.name}
                                  >
                                    <EntityImage entity={component} size="sm" />
                                  </div>
                                ))}
                              </div>
                            </>
                          ) : item.type === 'components' ? (
                            <span className="border border-[#4a4228] bg-[#1a1912] px-2 py-1 font-mono text-[9px] text-[#d5b85f]">
                              DIRECT
                            </span>
                          ) : (
                            <span className="font-mono text-[9px] text-[#566176]">
                              BRAK RECEPTURY
                            </span>
                          )}
                        </article>
                      ))}
                    </div>

                    <div className="mb-3 flex items-center justify-between border-t border-[#26303e] pt-4">
                      <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#667287]">
                        Zapotrzebowanie na komponenty
                      </p>
                      <span className="font-mono text-[9px] text-[#536075]">
                        ZSUMOWANE Z RECEPTUR
                      </span>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                      {workspace.components.map((component) => {
                        const decision = configuration.components.find(
                          (entry) => entry.apiName === component.apiName,
                        )
                        return (
                          <article
                            key={component.apiName}
                            className="flex items-center gap-3 border border-[#252f3e] bg-[#0b1018] p-3"
                          >
                            <div className="relative">
                              <EntityImage entity={component} />
                              <span className="absolute -bottom-1 -right-1 grid h-5 min-w-5 place-items-center border border-[#9c7f38] bg-[#d2ae51] px-1 font-mono text-[9px] font-black text-[#15120a]">
                                ×{component.requiredCount}
                              </span>
                            </div>
                            <div className="min-w-0 flex-1">
                              <h3 className="mb-2 truncate text-xs font-black text-[#e3e8ef]">
                                {component.name}
                              </h3>
                              <PrioritySelect
                                label={`Priorytet komponentu ${component.name}`}
                                value={decision?.priority ?? 'unset'}
                                onChange={(priority) =>
                                  changeComponentPriority(
                                    component.apiName,
                                    priority,
                                  )
                                }
                              />
                            </div>
                          </article>
                        )
                      })}
                    </div>
                  </section>
                </div>
                <aside className="space-y-5">
                  <section className="panel-cut border border-[#343527] bg-[#12140f] p-5">
                    <SectionHeading
                      icon={<SlidersHorizontal className="h-4 w-4" />}
                      eyebrow="Engine mix"
                      title="Wagi sygnałów"
                      count={3}
                    />
                    <div className="space-y-5">
                      <WeightControl
                        label="Early units"
                        value={configuration.weights.units}
                        color="#65a8cf"
                        onChange={(value) => changeWeight('units', value)}
                      />
                      <WeightControl
                        label="Komponenty"
                        value={configuration.weights.components}
                        color="#d2ae51"
                        onChange={(value) => changeWeight('components', value)}
                      />
                      <WeightControl
                        label="Augmenty"
                        value={configuration.weights.augments}
                        color="#a27bd6"
                        onChange={(value) => changeWeight('augments', value)}
                      />
                    </div>
                    <div
                      className={`mt-5 flex items-center justify-between border-t pt-4 ${
                        weightTotal === 100
                          ? 'border-[#303526] text-[#6fbe98]'
                          : 'border-[#513332] text-[#e18578]'
                      }`}
                    >
                      <span className="text-[10px] font-black uppercase tracking-[0.17em]">
                        Suma wag
                      </span>
                      <span className="font-mono text-lg font-bold">
                        {weightTotal}%
                      </span>
                    </div>
                  </section>

                  <section className="border border-[#252f3e] bg-[#0e141d] p-5">
                    <p className="mb-2 text-[10px] font-black uppercase tracking-[0.2em] text-[#75643a]">
                      Notatka z Academy
                    </p>
                    <p className="text-xs leading-5 text-[#8f9bad]">
                      {workspace.source.augmentTip ||
                        'Brak dodatkowej notatki dla tej kompozycji.'}
                    </p>
                  </section>

                  <section className="border border-[#252f3e] bg-[#0e141d] p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-[#667287]">
                          Stan eksportu
                        </p>
                        <h2 className="font-display text-base font-bold text-[#edf1f6]">
                          Gotowość
                        </h2>
                      </div>
                      <span className="font-mono text-xs text-[#d3b45e]">
                        {progress.percent}%
                      </span>
                    </div>
                    <div className="mb-4 h-1.5 overflow-hidden bg-[#1b2330]">
                      <div
                        className="h-full bg-[#d0ac51] transition-all"
                        style={{ width: `${progress.percent}%` }}
                      />
                    </div>
                    <label className="flex cursor-pointer items-start gap-3 border border-[#273141] bg-[#0b1018] p-3">
                      <input
                        type="checkbox"
                        checked={configuration.status === 'ready'}
                        disabled={progress.percent !== 100}
                        onChange={(event) =>
                          setConfiguration((current) =>
                            current
                              ? {
                                  ...current,
                                  status: event.target.checked
                                    ? 'ready'
                                    : 'draft',
                                }
                              : current,
                          )
                        }
                        className="mt-0.5 h-4 w-4 accent-[#d2ae51]"
                      />
                      <span>
                        <span className="block text-xs font-black text-[#dbe2eb]">
                          Gotowa dla silnika
                        </span>
                        <span className="mt-1 block text-[10px] leading-4 text-[#687589]">
                          Dostępne po ustawieniu wszystkich priorytetów.
                        </span>
                      </span>
                    </label>
                  </section>

                  <section className="border border-[#252f3e] bg-[#0e141d] p-5">
                    <p className="mb-2 text-[10px] font-black uppercase tracking-[0.2em] text-[#667287]">
                      Notatki własne
                    </p>
                    <textarea
                      value={configuration.notes}
                      onChange={(event) =>
                        setConfiguration((current) =>
                          current
                            ? { ...current, notes: event.target.value }
                            : current,
                        )
                      }
                      rows={5}
                      placeholder="Edge case’y, warunki wejścia, flex…"
                      className="field-control w-full resize-y rounded-sm p-3 text-xs leading-5 outline-none"
                    />
                  </section>
                </aside>
              </div>
            </>
          )}
        </section>
      </main>

      {notice ? (
        <div
          className={`fixed bottom-5 right-5 z-50 flex max-w-md items-center gap-3 border px-4 py-3 text-xs font-bold shadow-2xl ${
            notice.tone === 'ok'
              ? 'border-[#376c57] bg-[#10231b] text-[#8fd7b4]'
              : 'border-[#75453f] bg-[#2a1514] text-[#eda296]'
          }`}
          role="status"
        >
          {notice.tone === 'ok' ? (
            <Check className="h-4 w-4 shrink-0" />
          ) : (
            <CircleAlert className="h-4 w-4 shrink-0" />
          )}
          {notice.text}
        </div>
      ) : null}
    </div>
  )
}

export default App
