import type { Dispatch, SetStateAction } from 'react'
import { SlidersHorizontal } from 'lucide-react'
import StrategyEditor from './StrategyEditor'
import { SectionHeading, WeightControl } from './ConfiguratorControls'
import { emptyStrategy, type Configuration, type CompositionWorkspace } from './configuration'

const retiredRuleLabels: Record<string, string> = {
  openers: 'Alternatywny opener',
  item_overrides: 'Wyjątek itemowy',
  augment_conditions: 'Warunek augmentu',
}

export function ConfigurationSettings({
  configuration, workspace, setConfiguration, progress, weightTotal, changeWeight,
}: {
  configuration: Configuration
  workspace: CompositionWorkspace
  setConfiguration: Dispatch<SetStateAction<Configuration | null>>
  progress: { percent: number }
  weightTotal: number
  changeWeight: (key: keyof Configuration['weights'], value: number) => void
}) {
  return (
  <aside className="space-y-5">
    {!!configuration.retiredStrategyRules?.length && (
      <div role="note" className="mb-4 border border-amber-700 p-4 text-sm">
        <p>Po odświeżeniu wycofano nieaktualne reguły. Ich treść pozostaje zapisana w konfiguracji; sprawdź ustawienia przed oznaczeniem kompozycji jako gotowej.</p>
        <ul>{configuration.retiredStrategyRules.map((entry, index) => (
          <li key={index}>
                          {retiredRuleLabels[entry.kind] ?? 'Reguła'}: {String(entry.rule.reason ?? entry.rule.name ?? '')}
                          <span className="block">{entry.reason}</span>
                        </li>
        ))}</ul>
      </div>
    )}
    {workspace.strategyCatalog && <StrategyEditor value={configuration.strategy ?? emptyStrategy} catalog={workspace.strategyCatalog} augments={workspace.augments} onChange={strategy => setConfiguration(current => current ? {...current, strategy} : current)} />}
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
  )
}
