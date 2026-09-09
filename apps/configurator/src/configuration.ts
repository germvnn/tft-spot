import type { Strategy } from "./StrategyEditor"
import { readJson } from "./api"

export const emptyStrategy: Strategy = { openers: [], itemOverrides: [], augmentConditions: [] };

export type Priority =
  | 'unset'
  | 'essential'
  | 'high'
  | 'medium'
  | 'low'
  | 'avoid'
export type ConfigurationStatus = 'draft' | 'ready'

export type EntityCard = {
  apiName: string
  name: string
  imageUrl: string | null
  type?: string | null
}

export type UnitCard = EntityCard & {
  boardIndex: number | null
  stars: number | null
  items: EntityCard[]
}

export type ComponentCard = EntityCard & {
  requiredCount: number
}

export type ItemRecommendation = EntityCard & {
  components: EntityCard[]
}

export type AugmentCard = EntityCard & {
  disabledAtSource: boolean
}

export type PriorityDecision = {
  apiName: string
  priority: Priority
}

export type UnitPriorityDecision = PriorityDecision & { core: boolean }

export type Configuration = {
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
  retiredStrategyRules?: { kind: string; rule: Record<string, unknown>; reason: string }[]
  strategy?: Strategy
  notes: string
  updatedAt: string | null
}

export type CompositionSummary = {
  sourceId: string
  title: string
  slug: string | null
  position: number
  configured: boolean
}

export type SourceRefreshResult = {
  setNumber: number
  compositionCount: number
  addedSourceIds: string[]
  removedSourceIds: string[]
  reconciledSourceIds: string[]
  removedConfigurationSourceIds: string[]
}

export type CompositionWorkspace = {
  source: {
    sourceId: string
    title: string
    metaTitle: string | null
    slug: string | null
    set: number
    tier: string | null
    style: string | null
    difficulty: string | null
    updatedAt: string | null
    mainChampion: EntityCard | null
    augmentTip: string | null
    tips: { stage: string; tip: string }[]
  }
  strategyCatalog?: { champions: EntityCard[]; targets: EntityCard[]; items: EntityCard[] }
  finalUnits: UnitCard[]
  earlyUnits: UnitCard[]
  itemRecommendations: ItemRecommendation[]
  components: ComponentCard[]
  augments: AugmentCard[]
  configuration: Configuration
}

export async function loadWorkspace(url: string, init?: RequestInit): Promise<CompositionWorkspace> {
  const workspace = await readJson<CompositionWorkspace>(url, init)
  return { ...workspace, configuration: withUnitDefaults(workspace.configuration, workspace.earlyUnits) }
}

export function withUnitDefaults(configuration: Configuration, earlyUnits: UnitCard[]): Configuration {
  return {
    ...configuration,
    units: (configuration.units ?? Array.from(new Set(earlyUnits.map((unit) => unit.apiName)), (apiName) => ({ apiName, priority: 'medium' as const, core: false }))).map((unit) => ({ ...unit, core: unit.core ?? false })),
  }
}
