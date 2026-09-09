import {
  Boxes,
  Check,
  CheckCheck,
  ChevronRight,
  CircleAlert,
  CircleDot,
  ExternalLink,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Sparkles,
  Sword,
  UsersRound,
} from 'lucide-react'
import { useEffect, useRef } from 'react'
import { EntityImage, PrioritySelect, SectionHeading } from './ConfiguratorControls'
import { ConfigurationSettings } from './ConfigurationSettings'
import { useConfigurationEditor } from './useConfigurationEditor'

function App({ active = true }: { active?: boolean }) {
  const { compositions, selectedId, workspace, configuration, setConfiguration, baseline,
    query, setQuery, loadingList, loadingWorkspace, saving, bootstrapping, refreshingSource,
    notice, dirty, configuredCount, filteredCompositions, progress, weightTotal,
    selectComposition, changeComponentPriority, changeUnitCore, changeAugment, changeWeight,
    save, bootstrapAll, refreshSource } = useConfigurationEditor()

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
        <aside className="border-b border-[#252d3a] bg-[#0c1018] lg:sticky lg:top-32 lg:flex lg:h-[calc(100vh-8rem)] lg:flex-col lg:border-b-0 lg:border-r">
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

            <div className="mt-4 border border-[#2c3d4c] bg-[#0f141c] p-3">
              <div className="mb-2">
                <span className="text-[10px] font-black uppercase tracking-[0.16em] text-[#738da4]">
                  Źródło TFT Academy
                </span>
              </div>
              <button
                type="button"
                onClick={refreshSource}
                disabled={
                  loadingList ||
                  refreshingSource ||
                  bootstrapping ||
                  saving ||
                  dirty
                }
                className="secondary-button w-full"
              >
                <RefreshCw
                  className={`h-4 w-4 ${refreshingSource ? 'animate-spin' : ''}`}
                />
                {refreshingSource ? 'Odświeżam dane…' : 'Odśwież snapshot'}
              </button>
              <p className="mt-2 text-[10px] leading-4 text-[#667789]">
                Pobiera raw i assety, potem synchronizuje curated.
              </p>
            </div>

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
                  refreshingSource ||
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
            className="max-h-72 overflow-y-auto p-2 lg:min-h-0 lg:max-h-none lg:flex-1"
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
                    disabled={saving || bootstrapping || refreshingSource}
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
                        {composition.slug?.replace('set-18-', '') || 'brak sluga'}
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

        <fieldset disabled={bootstrapping || refreshingSource} className="min-w-0 border-0 p-0 m-0">
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
                        {workspace.source.slug ? (
                          <a
                            href={`https://tftacademy.com/tierlist/comps/${workspace.source.slug}`}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-[#aa9254] hover:text-[#e3c46f]"
                          >
                            TFT Academy <ExternalLink className="h-3 w-3" />
                          </a>
                        ) : (
                          <span>Brak linku źródłowego</span>
                        )}
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
                <ConfigurationSettings
                  configuration={configuration}
                  workspace={workspace}
                  setConfiguration={setConfiguration}
                  progress={progress}
                  weightTotal={weightTotal}
                  changeWeight={changeWeight}
                />
              </div>
            </>
          )}
        </fieldset>
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
