import StrategyEvidence, { type StrategyEvidenceData } from "./StrategyEvidence";
import { useEffect, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Download,
  FlaskConical,
  LoaderCircle,
  Save,
} from "lucide-react";
import "./simulator.css";

type Entity = { name: string; imageUrl: string | null };
type BoardUnit = Entity & { apiName: string; boardIndex: number | null; stars: number | null; items: (Entity & { apiName: string })[] };
type Review = {
  sourceId: string;
  verdict: string;
  expectedUnitFit: number | null;
  expectedScore: number | null;
  acceptableSourceIds?: string[];
  split?: "calibration" | "holdout";
  notes: string;
};
type Ranking = {
  sourceId: string;
  title: string;
  score: number | null;
  eligible: boolean;
  bestAugmentApiName: string | null;
  requiredAugmentApiName: string | null;
  weights: { units: number };
  evidence: StrategyEvidenceData & {
    units: { apiName: string; copies: number; core: boolean; points: number }[];
    components?: { apiName: string; ownedCount: number; matchedCount: number; points: number }[];
    unitFit: { coreShare: number; coreCount: number };
  };
  variants: {
    augmentApiName: string;
    eligible: boolean;
    score: number | null;
    dimensionScores: { units: number };
    weightedContributions: {
      units: number;
      components: number;
      augments: number;
    };
  }[];
};
type Case = {
  unitGold?: number;
  id: number;
  label: string;
  targetSourceId: string;
  targetTitle: string;
  spot: {
    units: { apiName: string; count: number }[];
    components: { apiName: string; count: number }[];
    offeredAugments: string[];
  };
  rankings: Ranking[];
  review: Review | null;
  referenceReview: Review | null;
  previousScores: Record<string, number | null> | null;
};
type Run = {
  id: string;
  seed: number;
  setNumber: number;
  count: number;
  createdAt: string;
  scoringVersion: string;
  entities: Record<string, Entity>;
  benchmark?: { targetCoverage: number; duplicateComponentCases: number; calibration: {reviewedCases: number; top3HitRate: number|null}; holdout: {reviewedCases: number; top3HitRate: number|null} };
  compositionBoards?: Record<string, BoardUnit[]>;
  cases: Case[];
};
type Summary = Pick<
  Run,
  "id" | "seed" | "count" | "createdAt" | "scoringVersion"
>;
const verdicts = {
  too_low: "Za nisko",
  about_right: "Trafna ocena",
  too_high: "Za wysoko",
  unrealistic: "Nierealistyczny spot",
};
async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const body = await response.json();
  if (!response.ok)
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Nie udało się wykonać operacji.",
    );
  return body;
}
function json(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  };
}

function CompositionBoard({ sourceId, title, frozen }: { sourceId: string; title: string; frozen?: BoardUnit[] }) {
  const [loaded, setLoaded] = useState<{ sourceId: string; units?: BoardUnit[]; error?: string } | null>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (frozen) return;
    const controller = new AbortController();
    api<{ finalUnits: BoardUnit[] }>(`/api/compositions/${encodeURIComponent(sourceId)}`, { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setLoaded({ sourceId, units: data.finalUnits }); })
      .catch((error: Error) => { if (!controller.signal.aborted) setLoaded({ sourceId, error: error.message }); });
    return () => controller.abort();
  }, [sourceId, frozen, retry]);
  const current = loaded?.sourceId === sourceId ? loaded : null;
  const units = frozen ?? current?.units;
  return <section className="sim-final-board" aria-label="Final composition">
    <p className="spot-eyebrow">REFERENCE BOARD</p>
    <h3>Final composition · {title} <small>{units?.length ?? ""}</small></h3>
    {!frozen && <p className="spot-hint">Podgląd z aktualnego konfiguratora — ta seria nie zawiera zapisanego składu.</p>}
    {!units && !current?.error && <p role="status">Wczytuję skład…</p>}
    {current?.error && !frozen && <p role="alert">Nie udało się pobrać składu. <button onClick={() => setRetry(value => value + 1)}>Spróbuj ponownie</button></p>}
    {units?.length === 0 && <p>Brak finalnego składu.</p>}
    <div className="sim-final-units">
      {units?.map((unit, index) => <article key={`${unit.apiName}-${index}`}>
        <div className="sim-final-unit-heading">
          {unit.imageUrl ? <img src={unit.imageUrl} alt="" /> : <span className="sim-unit-placeholder">{unit.name.slice(0, 2).toUpperCase()}</span>}
          <div><strong>{unit.name}</strong><small>HEX {unit.boardIndex ?? "—"} · {unit.stars ?? 1}★</small></div>
        </div>
        <div className="sim-final-items">
          {unit.items.length ? unit.items.map((item, itemIndex) => <span key={`${item.apiName}-${itemIndex}`} title={item.name}>
            {item.imageUrl ? <img src={item.imageUrl} alt={item.name} /> : <span>{item.name}</span>}
          </span>) : <small>Brak itemów</small>}
        </div>
      </article>)}
    </div>
  </section>;
}

export default function Simulator() {
  const [runs, setRuns] = useState<Summary[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [index, setIndex] = useState(0);
  const [seed, setSeed] = useState(42);
  const [setNumber, setSetNumber] = useState(18);
  const [count, setCount] = useState(50);
  const [mode, setMode] = useState("standard");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [drafts, setDrafts] = useState<Record<number, Review>>({});
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api<{ runs: Summary[] }>("/api/simulator/runs", {
      signal: controller.signal,
    })
      .then(async (data) => {
        if (controller.signal.aborted) return;
        setRuns(data.runs);
        if (data.runs[0]) {
          const latest = await api<Run>(
            `/api/simulator/runs/${data.runs[0].id}`,
            { signal: controller.signal },
          );
          if (!controller.signal.aborted) setRun(latest);
        }
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setMessage(error.message);
      });
    return () => controller.abort();
  }, [retry]);
  const open = async (id: string) => {
    setBusy(true);
    setMessage("");
    try {
      setRun(await api<Run>(`/api/simulator/runs/${id}`));
      setIndex(0);
      setDrafts({});
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const generate = async (replay = false) => {
    setBusy(true);
    setMessage("");
    try {
      const next = await api<Run>(
        replay && run
          ? `/api/simulator/runs/${run.id}/replay`
          : "/api/simulator/runs",
        json("POST", replay ? undefined : { seed, count, setNumber, mode }),
      );
      setRun(next);
      setRuns((current) => [next, ...current]);
      setIndex(0);
      setDrafts({});
      setMessage(`Zapisano serię ${next.count} przypadków.`);
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const scenario = run?.cases[index];
  const fallback =
    scenario?.rankings.find((r) => r.sourceId === scenario.targetSourceId) ??
    scenario?.rankings[0];
  const draft = scenario
    ? (drafts[scenario.id] ??
      scenario.review ?? {
        sourceId: fallback?.sourceId ?? "",
        verdict: "",
        expectedUnitFit: null,
        expectedScore: null,
        notes: "",
      })
    : null;
  const selected = scenario?.rankings.find(
    (r) => r.sourceId === draft?.sourceId,
  );
  const best =
    selected?.variants.find(
      (v) => v.augmentApiName === selected.bestAugmentApiName,
    ) ?? selected?.variants[0];
  const patch = (changes: Partial<Review>) => {
    if (scenario && draft)
      setDrafts((current) => ({
        ...current,
        [scenario.id]: { ...draft, ...changes },
      }));
  };
  const save = async (next: boolean) => {
    if (!run || !scenario || !draft || !draft.verdict) return;
    setBusy(true);
    setMessage("");
    try {
      const saved = await api<Review>(
        `/api/simulator/runs/${run.id}/reviews/${scenario.id}`,
        json("PUT", draft),
      );
      setRun((current) =>
        current
          ? {
              ...current,
              cases: current.cases.map((c) =>
                c.id === scenario.id ? { ...c, review: saved } : c,
              ),
            }
          : current,
      );
      setDrafts((current) => {
        const updated = { ...current };
        delete updated[scenario.id];
        return updated;
      });
      setMessage("Ocena zapisana.");
      if (next) setIndex((value) => Math.min(value + 1, run.cases.length - 1));
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const exportRun = () => {
    if (!run) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(run, null, 2)], { type: "application/json" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `tft-simulator-${run.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };
  const cards = (entries: { apiName: string; count?: number }[]) => (
    <div className="sim-entities">
      {entries.map((entry) => (
        <div key={entry.apiName}>
          {run?.entities[entry.apiName]?.imageUrl && (
            <img src={run.entities[entry.apiName].imageUrl!} alt="" />
          )}
          <span>{run?.entities[entry.apiName]?.name ?? entry.apiName}</span>
          {entry.count !== undefined && <b>×{entry.count}</b>}
        </div>
      ))}
    </div>
  );
  const unsaved = Object.keys(drafts).length > 0;
  return (
    <main className="spot-page">
      <div className="spot-intro">
        <div>
          <p className="spot-eyebrow">LABORATORIUM DOPASOWANIA</p>
          <h1>Symulator openerów</h1>
          <p>
            Porównuj spoty, oceniaj wyniki i buduj zestaw do kalibracji silnika.
          </p>
        </div>
        <FlaskConical size={34} />
      </div>
      <section className="spot-panel sim-toolbar">
        <label>
          Set
          <input
            aria-label="Set symulacji"
            type="number"
            min={1}
            value={setNumber}
            onChange={(e) => setSetNumber(Number(e.target.value))}
          />
        </label>
        <label>
          Liczba spotów
          <input
            aria-label="Liczba spotów"
            type="number"
            min={1}
            max={200}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
          />
        </label>
        <label>
          Tryb
          <select aria-label="Tryb generatora" value={mode} onChange={e=>setMode(e.target.value)}><option value="standard">Standardowy</option><option value="coverage">Przekrój kompozycji + duplikaty</option></select>
          Seed
          <input
            aria-label="Seed"
            type="number"
            min={0}
            max={2147483647}
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value))}
          />
        </label>
        <button
          className="primary-button"
          disabled={
            busy ||
            unsaved ||
            !Number.isInteger(count) ||
            count < 1 ||
            count > 200 ||
            !Number.isInteger(seed) ||
            seed < 0 ||
            !Number.isInteger(setNumber) ||
            setNumber < 1
          }
          onClick={() => generate()}
        >
          {busy ? (
            <LoaderCircle size={16} className="animate-spin" />
          ) : (
            <FlaskConical size={16} />
          )}
          Generuj serię
        </button>
        {run && (
          <button
            className="secondary-button"
            disabled={busy || unsaved}
            onClick={() => generate(true)}
          >
            Przelicz te same spoty
          </button>
        )}
      </section>
      <p className="spot-hint">
        Syntetyczne przypadki do oceny dopasowania, bez symulacji walk. Ten sam
        seed i dane dają te same spoty.{" "}
        {unsaved && "Masz niezapisane oceny — zapisz je przed zmianą serii."}
      </p>
      {message && (
        <p className="sim-message" role="status">
          {message}
          <button
            onClick={() => setRetry((value) => value + 1)}
            disabled={busy || unsaved}
          >
            Odśwież listę
          </button>
        </p>
      )}
      {runs.length > 0 && (
        <div className="sim-run-select">
          <label>
            Zapisana seria
            <select
              aria-label="Zapisana seria"
              value={run?.id ?? ""}
              disabled={busy || unsaved}
              onChange={(event) => open(event.target.value)}
            >
              <option value="" disabled>
                Wybierz serię
              </option>
              {runs.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {new Date(entry.createdAt).toLocaleString("pl")} ·{" "}
                  {entry.count} spotów · seed {entry.seed} ·{" "}
                  {entry.scoringVersion}
                </option>
              ))}
            </select>
          </label>
          <button
            className="secondary-button"
            onClick={exportRun}
            disabled={!run || unsaved}
          >
            <Download size={15} />
            Eksport JSON
          </button>
        </div>
      )}
      {run && scenario && draft && (
        <>
          <div className="sim-summary">
            <strong>
              {run.cases.filter((c) => c.review).length}/{run.count} ocenionych
            </strong>
            <span>
              {run.scoringVersion} · seed {run.seed}
              {run.benchmark && <span style={{display:'block'}}>Pokrycie: {run.benchmark.targetCoverage} kompozycji · {run.benchmark.duplicateComponentCases} spotów z duplikatami.
                {(['calibration','holdout'] as const).map(split=>{
                  const reviewed=run.cases.filter(c=>{const v=c.review??c.referenceReview;return v && v.verdict!=='unrealistic' && (v.split??'calibration')===split && (v.acceptableSourceIds?.length??0)>0;});
                  const hits=reviewed.filter(c=>c.rankings.filter(r=>r.eligible).slice(0,3).some(r=>(c.review??c.referenceReview)?.acceptableSourceIds?.includes(r.sourceId))).length;
                  return <span key={split} style={{display:'block'}}>{split==='holdout'?'Weryfikacja':'Kalibracja'}: {reviewed.length?`${Math.round(hits/reviewed.length*100)}% top 3 (${reviewed.length} spotów)`:'brak etykiet'}</span>;
                })}
              </span>}
            </span>
          </div>
          <div className="sim-case-buttons" aria-label="Przypadki symulacji">
            {run.cases.map((c, position) => (
              <button
                key={c.id}
                onClick={() => setIndex(position)}
                disabled={busy}
                aria-current={position === index ? "step" : undefined}
                className={c.review ? "reviewed" : ""}
              >
                {c.id}
                {drafts[c.id] ? "*" : ""}
              </button>
            ))}
          </div>
          <section className="spot-panel">
            <div className="spot-panel-heading">
              <h2>
                #{scenario.id} · {scenario.label}
              </h2>
              <div>
                <button
                  className="secondary-button"
                  aria-label="Poprzedni przypadek"
                  disabled={busy || index === 0}
                  onClick={() => setIndex(index - 1)}
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  className="secondary-button"
                  aria-label="Następny przypadek"
                  disabled={busy || index === run.cases.length - 1}
                  onClick={() => setIndex(index + 1)}
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
            <p className="spot-hint">
              Punkt odniesienia generatora: {scenario.targetTitle}. To nie jest
              etykieta poprawnej odpowiedzi.
            </p>
            <h3>Jednostki — liczba kopii{scenario.unitGold !== undefined ? ` · ${scenario.unitGold} golda` : ""}</h3>
            {cards(scenario.spot.units)}
            <h3>Komponenty</h3>
            {cards(scenario.spot.components)}
            <h3>Oferta augmentów</h3>
            {cards(
              scenario.spot.offeredAugments.map((apiName) => ({ apiName })),
            )}
          </section>
          <div className="sim-review-grid">
            <section className="spot-panel">
              <h2>Ranking silnika</h2>
              <div className="sim-ranking">
                {scenario.rankings
                  .filter((r) => r.eligible)
                  .slice(0, 8)
                  .map((r, position) => (
                    <button
                      key={r.sourceId}
                      onClick={() =>
                        patch({
                          sourceId: r.sourceId,
                          verdict: "",
                          expectedScore: null,
                          expectedUnitFit: null,
                        })
                      }
                    >
                      <span>
                        {position + 1}. {r.title}
                        <small>
                          {run.entities[r.bestAugmentApiName!]?.name}
                        </small>
                      </span>
                      <strong>{r.score?.toFixed(1)}/100</strong>
                    </button>
                  ))}
                {!scenario.rankings.some((r) => r.eligible) && (
                  <p>Brak dostępnych kierunków dla tej oferty.</p>
                )}
              </div>
            </section>
            <section className="spot-panel">
              <h2>Twoja ocena</h2>
              <label className="sim-field">
                Oceniana kompozycja
                <select
                  aria-label="Oceniana kompozycja"
                  value={draft.sourceId}
                  onChange={(e) =>
                    patch({
                      sourceId: e.target.value,
                      verdict: "",
                      expectedScore: null,
                      expectedUnitFit: null,
                    })
                  }
                >
                  {scenario.rankings.map((r) => (
                    <option key={r.sourceId} value={r.sourceId}>
                      {r.title}
                      {!r.eligible ? " — niedostępna" : ""}
                    </option>
                  ))}
                </select>
              </label>
              {selected && best && (
                <div className="sim-score">
                  <strong>
                    {selected.score === null
                      ? "Niedostępna"
                      : `${selected.score.toFixed(1)}/100`}
                  </strong>
                  <p>
                    Jednostki: {best.weightedContributions.units.toFixed(2)}/
                    {selected.weights.units} · komponenty:{" "}
                    {best.weightedContributions.components.toFixed(2)} ·
                    augment: {best.weightedContributions.augments.toFixed(2)}
                  </p>
                  <p>
                    Core: {selected.evidence.unitFit.coreCount} · udział{" "}
                    {(selected.evidence.unitFit.coreShare * 100).toFixed(1)}%
                  </p>
                  {!selected.eligible && (
                    <p>
                      {selected.requiredAugmentApiName
                        ? `Wymaga: ${run.entities[selected.requiredAugmentApiName]?.name}`
                        : "Brak polecanego augmentu w ofercie."}
                    </p>
                  )}
                  {scenario.previousScores && (
                    <p>
                      Poprzedni wynik:{" "}
                      {scenario.previousScores[selected.sourceId]?.toFixed(1) ??
                        "niedostępny"}
                    </p>
                  )}
                </div>
              )}
              {selected && <>
                {!!selected.evidence.components?.length && <div className="sim-component-evidence">
                  <h3>Dopasowanie komponentów</h3>
                  {selected.evidence.components.map(component => <p key={component.apiName}>
                    {run.entities[component.apiName]?.name ?? component.apiName}: wykorzystane {component.matchedCount}/{component.ownedCount}
                  </p>)}
                </div>}
              </>}
              {selected && <StrategyEvidence evidence={selected.evidence} />}
                <fieldset className="sim-accepted"><legend>Akceptowalne kierunki do top 3</legend>
                  <p className="spot-hint">Zaznacz wszystkie sensowne kierunki. Pusta lista oznacza brak etykiet do pomiaru trafności.</p>
                  {scenario.rankings.map(r=><label key={r.sourceId}><input type="checkbox" checked={draft.acceptableSourceIds?.includes(r.sourceId)??false} onChange={e=>patch({acceptableSourceIds:e.target.checked?[...(draft.acceptableSourceIds??[]),r.sourceId]:(draft.acceptableSourceIds??[]).filter(id=>id!==r.sourceId)})}/>{r.title}</label>)}
                </fieldset>
                <label>Zbiór oceny<select aria-label="Zbiór oceny" value={draft.split??'calibration'} onChange={e=>patch({split:e.target.value as 'calibration'|'holdout'})}><option value="calibration">Kalibracja</option><option value="holdout">Niezależna weryfikacja</option></select></label>
                <label className="sim-field">
                Jak oceniasz wynik?
                <select
                  aria-label="Ocena wyniku"
                  value={draft.verdict}
                  onChange={(e) => patch({ verdict: e.target.value })}
                >
                  <option value="">Wybierz ocenę</option>
                  {Object.entries(verdicts).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="sim-numbers">
                <label className="sim-field">
                  Twoje punkty za jednostki / {selected?.weights.units ?? 40}
                  <input
                    aria-label="Oczekiwane punkty jednostek"
                    type="number"
                    min={0}
                    max={selected?.weights.units ?? 40}
                    step={0.25}
                    disabled={!selected?.weights.units}
                    value={
                      draft.expectedUnitFit === null
                        ? ""
                        : Number(
                            (
                              (draft.expectedUnitFit *
                                (selected?.weights.units ?? 40)) /
                              100
                            ).toFixed(2),
                          )
                    }
                    onChange={(e) =>
                      patch({
                        expectedUnitFit:
                          e.target.value === ""
                            ? null
                            : (Number(e.target.value) * 100) /
                              (selected?.weights.units || 40),
                      })
                    }
                  />
                </label>
                <label className="sim-field">
                  Twój wynik całości / 100
                  <input
                    aria-label="Oczekiwany wynik"
                    type="number"
                    min={0}
                    max={100}
                    step={0.25}
                    value={draft.expectedScore ?? ""}
                    onChange={(e) =>
                      patch({
                        expectedScore:
                          e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                  />
                </label>
              </div>
              <label className="sim-field">
                Komentarz
                <textarea
                  aria-label="Komentarz do spotu"
                  rows={3}
                  value={draft.notes}
                  onChange={(e) => patch({ notes: e.target.value })}
                  placeholder="Co silnik przecenia lub pomija?"
                />
              </label>
              {scenario.referenceReview && (
                <p className="spot-hint">
                  Ocena poprzedniej wersji:{" "}
                  {
                    verdicts[
                      scenario.referenceReview.verdict as keyof typeof verdicts
                    ]
                  }{" "}
                  · {scenario.referenceReview.notes}
                </p>
              )}
              <div className="sim-save">
                {drafts[scenario.id] && (
                  <button
                    className="secondary-button"
                    disabled={busy}
                    onClick={() =>
                      setDrafts((current) => {
                        const next = { ...current };
                        delete next[scenario.id];
                        return next;
                      })
                    }
                  >
                    Odrzuć szkic
                  </button>
                )}
                <button
                  className="secondary-button"
                  disabled={busy || !draft.verdict}
                  onClick={() => save(false)}
                >
                  <Save size={15} />
                  Zapisz ocenę
                </button>
                <button
                  className="primary-button"
                  disabled={busy || !draft.verdict}
                  onClick={() => save(true)}
                >
                  Zapisz i następny
                  <ChevronRight size={15} />
                </button>
              </div>
            </section>
          </div>
          {selected && (
            <div className="sim-board-panel">
              <CompositionBoard sourceId={selected.sourceId} title={selected.title} frozen={run.compositionBoards?.[selected.sourceId]} />
            </div>
          )}
        </>
      )}
      {!run && !busy && (
        <div className="spot-empty">
          Wygeneruj pierwsze 50 spotów. Wyniki i zapisane oceny zostaną
          zachowane po odświeżeniu.
        </div>
      )}
    </main>
  );
}
