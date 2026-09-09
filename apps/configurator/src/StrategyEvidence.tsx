export type StrategyEvidenceData = {
  opener?: { name: string; alternatives: { name: string; unitFit: number }[] };
  itemPlan?: { available: boolean; reason?: string; fit: number | null; plans: { itemApiName: string; itemName: string; holderName: string; holderRole: string | null; targetName: string; holderBasis: string; targetBasis: string; upgradedHolder: boolean }[] } | null;
  componentFit?: { baseFit: number; combinedFit: number; planShare: number };
};
export default function StrategyEvidence({ evidence }: { evidence: StrategyEvidenceData }) {
  return <div className="strategy-evidence">
    {evidence.opener && evidence.opener.alternatives.length>1 && <p>Opener: <strong>{evidence.opener.name}</strong></p>}
    {evidence.itemPlan && <details><summary>Plan itemów · {evidence.itemPlan.plans.length} do złożenia</summary>
      <p>Wariant do rozważenia z obecnych komponentów; decyzja o slamie zależy również od siły planszy i lobby.</p>
      {!evidence.itemPlan.available ? <p>{evidence.itemPlan.reason==='inventory_above_stage_2_1_limit'?'Plan itemów obsługuje do 10 komponentów.':'Brakuje ocen itemów i holderów dla tej kompozycji.'} Tutaj użyto dopasowania komponentów.</p> : evidence.itemPlan.plans.length===0 ? <p>Brak potwierdzonego połączenia itemu, posiadanego holdera i docelowego składu.</p> : <ul>{evidence.itemPlan.plans.map((p,i)=><li key={i}><strong>{p.itemName}</strong> → {p.holderName} {p.upgradedHolder?'2★+':'1★'} ({p.holderRole??'rola nieznana'}) → docelowo {p.targetName}. {(p.holderBasis==='role_prior'||p.targetBasis==='role_prior')?'Dopasowanie częściowo oparte na roli — do kalibracji.':'Dopasowanie z buildu lub wyjątku eksperckiego.'}</li>)}</ul>}
      {evidence.componentFit && <p>Komponenty: {evidence.componentFit.baseFit.toFixed(1)} → {evidence.componentFit.combinedFit.toFixed(1)}/100 po uwzględnieniu planu ({Math.round(evidence.componentFit.planShare*100)}% wymiaru).</p>}
    </details>}
  </div>;
}
