type Card = { apiName: string; name: string; role?: string };
export type Strategy = {
  openers: { name: string; units: { apiName: string; core: boolean }[] }[];
  itemOverrides: { championApiName: string; itemApiName: string; fit: number; reason: string }[];
  augmentConditions: { augmentApiName: string; championApiName: string; minCopies: number; itemApiName: string | null; bonus: number; reason: string }[];
};
export default function StrategyEditor({ value, catalog, augments, onChange }: {
  value: Strategy; catalog: { champions: Card[]; targets: Card[]; items: Card[] }; augments: Card[]; onChange: (v: Strategy) => void;
}) {
  const select = (label: string, current: string, choices: Card[], change: (v: string) => void, optional = false) =>
    <label>{label}<select aria-label={label} value={current} onChange={e => change(e.target.value)}>
      {optional && <option value="">Bez warunku itemu</option>}
      {choices.map(c => <option key={c.apiName} value={c.apiName}>{c.name}{c.role ? ` · ${c.role}` : ''}</option>)}
    </select></label>;
  return <section className="strategy-editor panel-cut border border-[#252f3e] bg-[#0e141d] p-4">
    <h2>Reguły eksperckie</h2>
    <p>Wyjątki mają pierwszeństwo przed buildem z poradnika i profilem roli. Zapisz konfigurację, aby zastosować zmiany.</p>
    <details><summary>Alternatywne openery ({value.openers.length})</summary>
      <p>Każdy wariant oceniany jest osobno. Silnik wybiera najlepiej dopasowany; nie łączy ich jednostek.</p>
      {value.openers.map((o, i) => <fieldset key={i}><input aria-label={`Nazwa openera ${i+1}`} value={o.name} onChange={e => onChange({...value, openers: value.openers.map((x,j) => j===i ? {...x,name:e.target.value}:x)})}/>
        {catalog.champions.map(c => <div key={c.apiName}><label><input type="checkbox" checked={o.units.some(u => u.apiName===c.apiName)} onChange={e => onChange({...value,openers:value.openers.map((x,j) => j!==i?x:{...x,units:e.target.checked?[...x.units,{apiName:c.apiName,core:false}]:x.units.filter(u=>u.apiName!==c.apiName)})})}/>{c.name}</label>
        {o.units.some(u=>u.apiName===c.apiName) && <label>Core<input aria-label={`Core ${c.name} w ${o.name}`} type="checkbox" checked={o.units.find(u=>u.apiName===c.apiName)?.core??false} onChange={e=>onChange({...value,openers:value.openers.map((x,j)=>j!==i?x:{...x,units:x.units.map(u=>u.apiName===c.apiName?{...u,core:e.target.checked}:u)})})}/></label>}</div>)}
        <button onClick={()=>onChange({...value,openers:value.openers.filter((_,j)=>j!==i)})}>Usuń opener</button>
      </fieldset>)}
      <button disabled={value.openers.length>=8} onClick={()=>onChange({...value,openers:[...value.openers,{name:`Wariant ${value.openers.length+1}`,units:[]}]})}>Dodaj opener</button>
    </details>
    <details><summary>Wyjątki itemowe ({value.itemOverrides.length})</summary>
      <p>Dopasowanie 0 wyklucza item na tej postaci, 1 oznacza pełne dopasowanie. Specialist wymaga buildu lub jawnego wyjątku.</p>
      {value.itemOverrides.map((o,i)=>{
        const patch=(v: Partial<typeof o>)=>onChange({...value,itemOverrides:value.itemOverrides.map((x,j)=>j===i?{...x,...v}:x)});
        return <fieldset key={i}>{select(`Postać wyjątku ${i+1}`,o.championApiName,catalog.targets,v=>patch({championApiName:v}))}{select(`Item wyjątku ${i+1}`,o.itemApiName,catalog.items,v=>patch({itemApiName:v}))}
          <label>Dopasowanie<input type="number" min="0" max="1" step="0.05" value={o.fit} onChange={e=>patch({fit:Number(e.target.value)})}/></label>
          <label>Uzasadnienie<input value={o.reason} onChange={e=>patch({reason:e.target.value})}/></label>
          <button onClick={()=>onChange({...value,itemOverrides:value.itemOverrides.filter((_,j)=>j!==i)})}>Usuń wyjątek</button></fieldset>;
      })}
      <button disabled={!catalog.targets.length||!catalog.items.length} onClick={()=>onChange({...value,itemOverrides:[...value.itemOverrides,{championApiName:catalog.targets[0].apiName,itemApiName:catalog.items[0].apiName,fit:0,reason:''}]})}>Dodaj wyjątek</button>
    </details>
    <details><summary>Warunki augmentów ({value.augmentConditions.length})</summary>
      <p>Premia działa, gdy masz wymaganą liczbę kopii i możesz złożyć wskazany item dla tej postaci. Łączna korekta wynosi najwyżej ±20 punktów wymiaru augmentu.</p>
      {value.augmentConditions.map((o,i)=>{
        const patch=(v:Partial<typeof o>)=>onChange({...value,augmentConditions:value.augmentConditions.map((x,j)=>j===i?{...x,...v}:x)});
        return <fieldset key={i}>{select(`Augment warunku ${i+1}`,o.augmentApiName,augments,v=>patch({augmentApiName:v}))}{select(`Postać warunku ${i+1}`,o.championApiName,catalog.champions,v=>patch({championApiName:v}))}{select(`Item warunku ${i+1}`,o.itemApiName??'',catalog.items,v=>patch({itemApiName:v||null}),true)}
          <label>Minimum kopii<input type="number" min="1" max="4" value={o.minCopies} onChange={e=>patch({minCopies:Number(e.target.value)})}/></label>
          <label>Korekta<input type="number" min="-20" max="20" value={o.bonus} onChange={e=>patch({bonus:Number(e.target.value)})}/></label>
          <label>Uzasadnienie<input value={o.reason} onChange={e=>patch({reason:e.target.value})}/></label>
          <button onClick={()=>onChange({...value,augmentConditions:value.augmentConditions.filter((_,j)=>j!==i)})}>Usuń warunek</button></fieldset>;
      })}
      <button disabled={!augments.length||!catalog.champions.length} onClick={()=>onChange({...value,augmentConditions:[...value.augmentConditions,{augmentApiName:augments[0].apiName,championApiName:catalog.champions[0].apiName,itemApiName:null,minCopies:2,bonus:10,reason:''}]})}>Dodaj warunek</button>
    </details>
  </section>;
}
