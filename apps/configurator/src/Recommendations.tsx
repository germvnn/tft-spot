import { readJson as request } from "./api";
import StrategyEvidence, { type StrategyEvidenceData } from "./StrategyEvidence";
import { useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  Boxes,
  ChevronRight,
  LoaderCircle,
  Minus,
  RotateCcw,
  Search,
  Sparkles,
  UsersRound,
} from "lucide-react";
import "./recommendations.css";

type Card = {
  apiName: string;
  name: string;
  imageUrl: string | null;
  setNumber?: number;
};
type Champion = Card & { cost: number; role?: string };
type Augment = Card & { tier: number; description: string | null };
type Catalog = {
  setNumbers: number[];
  champions: Champion[];
  components: Card[];
  augments: Augment[];
};
type Dimension = "units" | "components" | "augments";
type Variant = {
  augmentApiName: string;
  eligible: boolean;
  reason: string | null;
  score: number | null;
  dimensionScores: Record<Dimension, number>;
  weightedContributions: Record<Dimension, number>;
  augmentContext?: { adjustment: number; conditions: { reason: string; matched: boolean; bonus: number }[] };
};
type Result = {
  sourceId: string;
  title: string;
  score: number | null;
  eligible: boolean;
  bestAugmentApiName: string | null;
  requiredAugmentApiName: string | null;
  mainChampion: Card | null;
  finalUnits: Card[];
  tier: string | null;
  style: string | null;
  weights: Record<Dimension, number>;
  variants: Variant[];
  assessment?: string;
  resourceFit?: { units: number; components: number };
  evidence: StrategyEvidenceData & {
    units: { apiName: string; copies: number; points: number; core?: boolean }[];
    unitFit?: { coreCount: number; coreShare: number; coreContribution: number; supportContribution: number };
    components: {
      apiName: string;
      ownedCount: number;
      matchedCount: number;
      points: number;
    }[];
  };
};
type Response = {
  recommendations: Result[];
  skipped: { sourceId: string; reason: string }[];
};
type Counts = Record<string, number>;
const costColors: Record<number, string> = {
  1: "#8994a6",
  2: "#59be88",
  3: "#5b9ff0",
};
const tierNames: Record<number, string> = {
  1: "Silver",
  2: "Gold",
  3: "Prismatic",
};
const labels: Record<Dimension, string> = {
  units: "Jednostki",
  components: "Komponenty",
  augments: "Augment",
};


function Picture({
  card,
  className = "",
}: {
  card?: Card | null;
  className?: string;
}) {
  return (
    <span className={`spot-picture ${className}`}>
      <span aria-hidden="true">{card?.name.slice(0, 2) ?? "?"}</span>
      {card?.imageUrl && (
        <img
          src={card.imageUrl}
          alt=""
          loading="lazy"
          onError={(event) => {
            event.currentTarget.style.display = "none";
          }}
        />
      )}
    </span>
  );
}

function CounterCard({
  card,
  count,
  color,
  onChange,
}: {
  card: Card;
  count: number;
  color: string;
  onChange: (delta: number) => void;
}) {
  return (
    <div
      className={`spot-counter ${count ? "selected" : ""}`}
      style={{ "--cost-color": color } as React.CSSProperties}
    >
      <button
        type="button"
        className="counter-main"
        title={"role" in card ? String(card.role || "Brak roli w źródle") : card.name}
        aria-label={`${card.name}: ${count} kopii. Dodaj 1`}
        onClick={() => onChange(1)}
        onContextMenu={(event) => {
          event.preventDefault();
          onChange(-1);
        }}
      >
        <Picture card={card} />
        <span className="counter-name">{card.name}</span>
        <span className="counter-value" aria-live="polite">
          {count}
        </span>
      </button>
      <button
        type="button"
        className="counter-minus"
        aria-label={`Odejmij 1: ${card.name}`}
        disabled={count === 0}
        onClick={() => onChange(-1)}
      >
        <Minus size={12} />
      </button>
    </div>
  );
}

export default function Recommendations({ active }: { active: boolean }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [setNumber, setSetNumber] = useState<number | null>(null);
  const [units, setUnits] = useState<Counts>({});
  const [components, setComponents] = useState<Counts>({});
  const [unitSearch, setUnitSearch] = useState("");
  const [rarity, setRarity] = useState(2);
  const [offers, setOffers] = useState(["", "", ""]);
  const [augmentSearch, setAugmentSearch] = useState(["", "", ""]);
  const [result, setResult] = useState<Response | null>(null);
  const [loading, setLoading] = useState(false);
  const [previousActive, setPreviousActive] = useState(active);
  const pending = useRef<AbortController | null>(null);
  const resultsRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    request<Catalog>("/api/spot-catalog", { signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        setError(null);
        setCatalog(data);
        setSetNumber((current) =>
          current !== null && data.setNumbers.includes(current)
            ? current
            : (data.setNumbers[0] ?? null),
        );
      })
      .catch((failure: Error) => {
        if (!controller.signal.aborted) setError(failure.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setCatalogLoading(false);
      });
    return () => controller.abort();
  }, [active, retry]);

  useEffect(() => {
    if (!active) pending.current?.abort();
  }, [active]);
  useEffect(() => () => pending.current?.abort(), []);

  if (previousActive !== active) {
    setPreviousActive(active);
    setResult(null);
    setLoading(false);
    setCatalogLoading(active);
  }

  const invalidate = () => {
    pending.current?.abort();
    setResult(null);
    setLoading(false);
    setError(null);
  };
  const changeCount = (
    kind: "units" | "components",
    name: string,
    delta: number,
  ) => {
    invalidate();
    const setter = kind === "units" ? setUnits : setComponents;
    setter((current) => {
      const next = { ...current };
      const count = Math.max(0, Math.min(99, (next[name] ?? 0) + delta));
      if (count) next[name] = count;
      else delete next[name];
      return next;
    });
  };
  const clear = () => {
    invalidate();
    setUnits({});
    setComponents({});
    setOffers(["", "", ""]);
    setAugmentSearch(["", "", ""]);
    setUnitSearch("");
  };
  const unitCatalog =
    catalog?.champions.filter(
      (card) => card.setNumber === setNumber && [1, 2, 3].includes(card.cost),
    ) ?? [];
  const componentCatalog =
    catalog?.components.filter((card) => card.setNumber === setNumber) ?? [];
  const augmentCatalog =
    catalog?.augments.filter(
      (card) => card.setNumber === setNumber && card.tier === rarity,
    ) ?? [];
  const cards = new Map<string, Card>(
    [
      ...(catalog?.champions ?? []),
      ...(catalog?.components ?? []),
      ...(catalog?.augments ?? []),
    ].map((card) => [card.apiName, card]),
  );
  const selectedOffers = offers.filter(Boolean);
  const totalUnits = Object.values(units).reduce(
    (sum, value) => sum + value,
    0,
  );
  const totalComponents = Object.values(components).reduce(
    (sum, value) => sum + value,
    0,
  );

  const generate = async () => {
    if (!setNumber || !selectedOffers.length) return;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await request<Response>("/api/recommendations", {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          setNumber,
          offeredAugments: selectedOffers,
          units: Object.entries(units).map(([apiName, count]) => ({
            apiName,
            stars: 1,
            count,
          })),
          components: Object.entries(components).map(([apiName, count]) => ({
            apiName,
            count,
          })),
        }),
      });
      if (controller.signal.aborted) return;
      setResult(data);
      requestAnimationFrame(() =>
        resultsRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        }),
      );
    } catch (failure) {
      if (!controller.signal.aborted) setError((failure as Error).message);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };
  const eligible =
    result?.recommendations.filter((entry) => entry.eligible) ?? [];
  const unavailable =
    result?.recommendations.filter((entry) => !entry.eligible) ?? [];

  return (
    <main className="spot-page">
      <div className="spot-intro">
        <div>
          <p className="spot-eyebrow">STAGE 2-1 · WYBÓR KIERUNKU</p>
          <h1>Jaki masz spot?</h1>
          <p>
            Dodaj to, co masz. Wybierz oferowane augmenty. Znajdź swój kierunek.
          </p>
        </div>
        <div className="spot-intro-actions">
          {catalog && catalog.setNumbers.length > 1 ? (
            <label>
              Set
              <select
                aria-label="Set"
                value={setNumber ?? ""}
                onChange={(event) => {
                  clear();
                  setSetNumber(Number(event.target.value));
                }}
              >
                {catalog.setNumbers.map((number) => (
                  <option key={number} value={number}>
                    Set {number}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <span className="spot-set">SET {setNumber ?? "—"}</span>
          )}
          <button type="button" className="secondary-button" onClick={clear}>
            <RotateCcw size={14} />
            Wyczyść spot
          </button>
        </div>
      </div>
      {catalogLoading ? (
        <div className="spot-empty" role="status">
          <LoaderCircle className="animate-spin" />
          Ładowanie jednostek, augmentów i komponentów…
        </div>
      ) : !catalog ? (
        <div className="spot-error" role="alert">
          {error ?? "Brak katalogu danych."}
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setCatalogLoading(true);
              setError(null);
              setRetry((value) => value + 1);
            }}
          >
            Spróbuj ponownie
          </button>
        </div>
      ) : (
        <>
          <section className="spot-panel" aria-labelledby="units-title">
            <div className="spot-panel-heading">
              <div>
                <span className="spot-step">01</span>
                <UsersRound size={19} />
                <h2 id="units-title">Twoje jednostki</h2>
                <span className="spot-chip">{totalUnits} kopii</span>
              </div>
              <label className="spot-search">
                <Search size={15} />
                <input
                  aria-label="Szukaj jednostki"
                  placeholder="Szukaj jednostki…"
                  value={unitSearch}
                  onChange={(event) => setUnitSearch(event.target.value)}
                />
              </label>
            </div>
            <p className="spot-hint">
              Lewy przycisk +1 · prawy −1 · 2★ = 3 kopie · uwzględnij board i
              ławkę
            </p>
            {[1, 2, 3].map((cost) => (
              <div className="spot-cost-group" key={cost}>
                <div
                  className="spot-cost-label"
                  style={{ color: costColors[cost] }}
                >
                  <span>{"◆".repeat(cost)}</span> {cost} GOLD
                </div>
                <div className="spot-counter-grid">
                  {unitCatalog
                    .filter(
                      (unit) =>
                        unit.cost === cost &&
                        unit.name
                          .toLocaleLowerCase()
                          .includes(unitSearch.toLocaleLowerCase()),
                    )
                    .map((unit) => (
                      <CounterCard
                        key={unit.apiName}
                        card={unit}
                        count={units[unit.apiName] ?? 0}
                        color={costColors[cost]}
                        onChange={(delta) =>
                          changeCount("units", unit.apiName, delta)
                        }
                      />
                    ))}
                </div>
              </div>
            ))}
            {!unitCatalog.some((unit) =>
              unit.name
                .toLocaleLowerCase()
                .includes(unitSearch.toLocaleLowerCase()),
            ) && (
              <p className="spot-hint">
                Brak jednostek pasujących do wyszukiwania.
              </p>
            )}
          </section>

          <section className="spot-panel" aria-labelledby="augments-title">
            <div className="spot-panel-heading">
              <div>
                <span className="spot-step">02</span>
                <Sparkles size={19} />
                <h2 id="augments-title">Oferowane augmenty</h2>
                <span className="spot-chip">{selectedOffers.length}/3</span>
              </div>
              <label className={`spot-rarity rarity-${rarity}`}>
                Poziom augmentów
                <select
                  aria-label="Poziom augmentów"
                  value={rarity}
                  onChange={(event) => {
                    invalidate();
                    setRarity(Number(event.target.value));
                    setOffers(["", "", ""]);
                    setAugmentSearch(["", "", ""]);
                  }}
                >
                  {[1, 2, 3].map((tier) => (
                    <option key={tier} value={tier}>
                      {tierNames[tier]}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="spot-hint">
              Wprowadź opcje z ekranu wyboru. Silnik oceni każdą osobno. Możesz
              zacząć od jednej.
            </p>
            <div className="spot-augment-grid">
              {offers.map((selected, index) => {
                const augment = catalog.augments.find(
                  (entry) => entry.apiName === selected,
                );
                const options = augmentCatalog.filter(
                  (entry) =>
                    entry.apiName === selected ||
                    entry.name
                      .toLocaleLowerCase()
                      .includes(augmentSearch[index].toLocaleLowerCase()),
                );
                return (
                  <article
                    key={index}
                    className={`spot-augment rarity-${rarity} ${selected ? "chosen" : ""}`}
                  >
                    <div className="augment-slot-heading">
                      <span>OPCJA 0{index + 1}</span>
                      <span>{tierNames[rarity]}</span>
                    </div>
                    <div className="augment-preview">
                      <Picture card={augment} />
                      <strong>{augment?.name ?? "Wybierz augment"}</strong>
                    </div>
                    <input
                      className="field-control"
                      aria-label={`Szukaj augmentu ${index + 1}`}
                      placeholder="Szukaj po nazwie…"
                      value={augmentSearch[index]}
                      onChange={(event) =>
                        setAugmentSearch((current) =>
                          current.map((value, slot) =>
                            slot === index ? event.target.value : value,
                          ),
                        )
                      }
                    />
                    <select
                      className="field-control"
                      aria-label={`Augment ${index + 1}`}
                      value={selected}
                      onChange={(event) => {
                        invalidate();
                        setOffers((current) =>
                          current.map((value, slot) =>
                            slot === index ? event.target.value : value,
                          ),
                        );
                      }}
                    >
                      <option value="">
                        Wybierz z listy ({options.length})
                      </option>
                      {options.map((entry) => (
                        <option
                          key={entry.apiName}
                          value={entry.apiName}
                          disabled={
                            entry.apiName !== selected &&
                            offers.includes(entry.apiName)
                          }
                        >
                          {entry.name}
                        </option>
                      ))}
                    </select>
                    <p className="augment-description">
                      {augment?.description?.replace(/<[^>]*>/g, "") ??
                        "Wybór augmentu może otworzyć nowy kierunek."}
                    </p>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="spot-panel" aria-labelledby="components-title">
            <div className="spot-panel-heading">
              <div>
                <span className="spot-step">03</span>
                <Boxes size={19} />
                <h2 id="components-title">Twoje komponenty</h2>
                <span className="spot-chip">{totalComponents} szt.</span>
              </div>
            </div>
            <p className="spot-hint">
              Lewy przycisk +1 · prawy −1 · policz także komponenty założone na
              jednostki.
            </p>
            <div className="spot-counter-grid component-grid">
              {componentCatalog.map((component) => (
                <CounterCard
                  key={component.apiName}
                  card={component}
                  count={components[component.apiName] ?? 0}
                  color="#c4a661"
                  onChange={(delta) =>
                    changeCount("components", component.apiName, delta)
                  }
                />
              ))}
            </div>
          </section>

          <div className="spot-generate">
            <div>
              <strong>
                {totalUnits} kopii jednostek <span>·</span> {totalComponents}{" "}
                komponentów <span>·</span> {selectedOffers.length} augmentów
              </strong>
              <p>
                {selectedOffers.length
                  ? "Gotowe? Sprawdź, które kompozycje wykorzystają Twój spot."
                  : "Wybierz co najmniej jeden oferowany augment."}
              </p>
            </div>
            <button
              type="button"
              className="primary-button"
              disabled={loading || !selectedOffers.length || !setNumber}
              onClick={generate}
            >
              {loading ? (
                <LoaderCircle size={18} className="animate-spin" />
              ) : (
                <ArrowDown size={18} />
              )}
              {loading ? "Oceniam spot…" : "Pokaż rekomendacje"}
            </button>
          </div>
          {error && (
            <div className="spot-error" role="alert">
              {error}
            </div>
          )}
          <section
            ref={resultsRef}
            className="spot-results"
            aria-labelledby="ranking-title"
            aria-busy={loading}
          >
            <div className="spot-ranking-heading">
              <div>
                <p className="spot-eyebrow">TWÓJ NASTĘPNY KIERUNEK</p>
                <h2 id="ranking-title">Ranking kompozycji</h2>
              </div>
              {result && (
                <span className="spot-chip">
                  {eligible.length} dostępnych kierunków
                </span>
              )}
            </div>
            {!result ? (
              <div className="spot-empty" role="status">
                {loading
                  ? "Porównuję Twój spot z konfiguracjami kompozycji…"
                  : "Tutaj zobaczysz dopasowanie, polecany augment i powody rekomendacji."}
              </div>
            ) : (
              <>
                {!eligible.length && (
                  <div className="spot-empty">
                    Brak rekomendacji dla tych augmentów. Sprawdź pozostałe
                    opcje lub priorytety kompozycji w konfiguratorze.
                  </div>
                )}
                {eligible.map((entry, index) => {
                  const best = entry.variants.find(
                    (variant) =>
                      variant.augmentApiName === entry.bestAugmentApiName,
                  )!;
                  const matchedUnits = entry.evidence.units.filter(
                    (unit) => unit.points > 0,
                  );
                  const matchedComponents = entry.evidence.components.filter(
                    (component) => component.points > 0,
                  );
                  return (
                    <article
                      key={entry.sourceId}
                      className={`spot-result ${index === 0 ? "first" : ""}`}
                    >
                      <div className="result-main">
                        <span className="result-position">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <Picture card={entry.mainChampion} />
                        <div className="result-title">
                          <div className="result-meta">
                            <span className="spot-eyebrow">
                              {entry.style ?? "Kierunek"}
                            </span>
                            <span className="result-tier">
                              TIER {entry.tier || "—"}
                            </span>
                          </div>
                          <h3>{entry.title}</h3>
                          <div className="result-augment">
                            <Picture
                              card={cards.get(entry.bestAugmentApiName!)}
                            />
                            <span>
                              Wybierz{" "}
                              <strong>
                                {cards.get(entry.bestAugmentApiName!)?.name ??
                                  entry.bestAugmentApiName}
                              </strong>
                            </span>
                          </div>
                        </div>
                        <div className="result-score">
                          <strong>{entry.score!.toFixed(1)}</strong>
                          <span>/100</span>
                          <small>DOPASOWANIE</small>
                        </div>
                      </div>
                      <div className="result-board">
                        {entry.finalUnits.map((unit, position) => (
                          <div
                            key={`${unit.apiName}-${position}`}
                            title={unit.name}
                          >
                            <Picture card={unit} />
                            <span>{unit.name}</span>
                          </div>
                        ))}
                      </div>
                      <div className="result-dimensions">
                        {(
                          ["units", "components", "augments"] as Dimension[]
                        ).map((dimension) => (
                          <div key={dimension}>
                            <div>
                              <span>{labels[dimension]}</span>
                              <strong>
                                +
                                {best.weightedContributions[dimension].toFixed(
                                  1,
                                )}
                                <small> / {entry.weights[dimension]}</small>
                              </strong>
                            </div>
                            <meter
                              min={0}
                              max={100}
                              value={best.dimensionScores[dimension]}
                              aria-label={`${labels[dimension]}: ${best.dimensionScores[dimension].toFixed(1)} na 100`}
                            />
                          </div>
                        ))}
                      </div>
                      <div className="result-reasons">
                    {entry.evidence.unitFit && <p><UsersRound size={15} /><span>
                      {entry.evidence.unitFit.coreCount > 0
                        ? `Core (${(entry.evidence.unitFit.coreShare * 100).toFixed(1)}% udziału): +${(entry.evidence.unitFit.coreContribution * entry.weights.units / 100).toFixed(1)} pkt · wsparcie: +${(entry.evidence.unitFit.supportContribution * entry.weights.units / 100).toFixed(1)} pkt`
                        : 'Brak oznaczonych core — każda jednostka openera ma równy udział w ocenie.'}
                    </span></p>}

                        <p>
                          <UsersRound size={15} />
                          <span>
                            {matchedUnits.length
                              ? matchedUnits
                                  .map(
                                    (unit) =>
                                      `${cards.get(unit.apiName)?.name ?? unit.apiName} ×${unit.copies}`,
                                  )
                                  .join(" · ")
                              : "Brak posiadanych jednostek wspierających ten opener."}
                          </span>
                        </p>
                        <p>
                          <Boxes size={15} />
                          <span>
                            {matchedComponents.length
                              ? matchedComponents
                                  .map(
                                    (component) =>
                                      `${cards.get(component.apiName)?.name ?? component.apiName}: wykorzystane ${component.matchedCount}/${component.ownedCount}`,
                                  )
                                  .join(" · ")
                              : "Brak dopasowanych komponentów w Twoim spocie."}
                          </span>
                        </p>
                        {entry.requiredAugmentApiName && (
                          <p>
                            <Sparkles size={15} />
                            <span>
                              Wybrany augment spełnia warunek konieczny tej
                              kompozycji.
                            </span>
                          </p>
                        )}
                      </div>
                      <StrategyEvidence evidence={entry.evidence} />
                      <details>
                        <summary>
                          Porównaj oferowane augmenty <ChevronRight size={14} />
                        </summary>
                        <div className="variant-list">
                          {entry.variants.map((variant) => (
                            <div key={variant.augmentApiName}>
                              <span>
                                {cards.get(variant.augmentApiName)?.name ?? variant.augmentApiName}
                                {variant.augmentContext?.conditions.map((c,i)=><small key={i} style={{display:'block'}}> {c.matched?'Spełniony':'Niespełniony'}: {c.reason}{c.matched?` (${c.bonus>0?'+':''}${c.bonus})`:''}</small>)}
                              </span>
                              <strong>
                                {variant.eligible
                                  ? `${variant.score!.toFixed(1)}/100`
                                  : variant.reason ===
                                      "requires_essential_augment"
                                    ? "Nie spełnia wymogu Core"
                                    : variant.reason === "augment_avoided"
                                      ? "Odrzucony w konfiguracji"
                                      : "Nieoceniony dla tej kompozycji"}
                              </strong>
                            </div>
                          ))}
                        </div>
                      </details>
                    </article>
                  );
                })}
                {unavailable.length > 0 && (
                  <details className="spot-unavailable">
                    <summary>
                      Pozostałe kompozycje — {unavailable.length} bez pełnej oceny lub z blokadą
                    </summary>
                    {unavailable.map((entry) => (
                      <div key={entry.sourceId}>
                        <span>{entry.title}</span>
                        <span>
                          {entry.requiredAugmentApiName
                            ? `Wymaga: ${cards.get(entry.requiredAugmentApiName)?.name ?? entry.requiredAugmentApiName}`
                            : entry.assessment === "unassessed"
                              ? `Augment nieoceniony · jednostki ${entry.resourceFit?.units.toFixed(1) ?? '—'}/100 · komponenty ${entry.resourceFit?.components.toFixed(1) ?? '—'}/100`
                              : "Oferowane augmenty odrzucone w konfiguracji"}
                        </span>
                      </div>
                    ))}
                  </details>
                )}
                {result.skipped.length > 0 && (
                  <p className="spot-hint">
                    Pominięto {result.skipped.length} kompozycji bez gotowej
                    konfiguracji. Możesz je przygotować w zakładce Konfigurator.
                  </p>
                )}
              </>
            )}
          </section>
        </>
      )}
    </main>
  );
}
