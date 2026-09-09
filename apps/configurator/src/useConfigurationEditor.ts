import { useEffect, useMemo, useRef, useState } from 'react'
import { readJson } from './api'
import {
  loadWorkspace, withUnitDefaults, type CompositionSummary, type CompositionWorkspace,
  type Configuration, type Priority, type SourceRefreshResult,
} from './configuration'

export function useConfigurationEditor() {
  const operationInProgress = useRef(false)
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
  const [refreshingSource, setRefreshingSource] = useState(false)
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
      .finally(() => { if (!controller.signal.aborted) setLoadingList(false) })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!selectedId) return
    const controller = new AbortController()
    loadWorkspace(`/api/compositions/${selectedId}`, {
      signal: controller.signal,
    })
      .then((nextWorkspace) => {
        if (controller.signal.aborted) return
        setWorkspace(nextWorkspace)
        setConfiguration(nextWorkspace.configuration)
        setBaseline(nextWorkspace.configuration)
      })
      .catch((error: unknown) => {
        if ((error as Error).name !== 'AbortError') {
          setNotice({ tone: 'error', text: (error as Error).message })
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoadingWorkspace(false) })
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
    if (sourceId === selectedId || operationInProgress.current) return
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
    if (operationInProgress.current || loadingWorkspace) {
      return { saved: false as const, error: 'Poczekaj na zakończenie bieżącej operacji.' }
    }
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

    operationInProgress.current = true
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
      // Keep edits made after the request was sent; only advance the saved baseline.
      setConfiguration(current => current === configuration ? saved : current)
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
      operationInProgress.current = false
      setSaving(false)
    }
  }

  const bootstrapAll = async () => {
    if (operationInProgress.current || loadingWorkspace) return
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

    operationInProgress.current = true
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
      operationInProgress.current = false
      setBootstrapping(false)
    }
  }

  const refreshSource = async () => {
    if (operationInProgress.current || loadingWorkspace) return
    if (dirty) {
      setNotice({
        tone: 'error',
        text: 'Najpierw zapisz albo cofnij zmiany bieżącej kompozycji.',
      })
      return
    }

    const confirmed = window.confirm(
      'Pobrać pełny snapshot TFT Academy i zsynchronizować curated data?\n\nNowe kompozycje zostaną dodane jako ready. Konfiguracje kompozycji usuniętych ze źródła zostaną skasowane.',
    )
    if (!confirmed) return

    operationInProgress.current = true
    setRefreshingSource(true)
    setLoadingList(true)
    setNotice(null)
    try {
      const result = await readJson<SourceRefreshResult>(
        '/api/compositions/refresh-source',
        { method: 'POST' },
      )
      const { compositions: entries } = await readJson<{
        compositions: CompositionSummary[]
      }>('/api/compositions')
      const nextSelectedId =
        selectedId && entries.some((entry) => entry.sourceId === selectedId)
          ? selectedId
          : entries[0]?.sourceId ?? null

      setCompositions(entries)
      setSelectedId(nextSelectedId)
      if (nextSelectedId) {
        setLoadingWorkspace(true)
        const nextWorkspace = await loadWorkspace(
          `/api/compositions/${nextSelectedId}`,
        )
        setWorkspace(nextWorkspace)
        setConfiguration(nextWorkspace.configuration)
        setBaseline(nextWorkspace.configuration)
      } else {
        setWorkspace(null)
        setConfiguration(null)
        setBaseline(null)
      }

      setNotice({
        tone: 'ok',
        text:
          `Odświeżono ${result.compositionCount} kompozycji · ` +
          `nowe: ${result.addedSourceIds.length} · ` +
          `usunięte: ${result.removedSourceIds.length} · ` +
          `zapisane konfiguracje: ${result.reconciledSourceIds.length}.`,
      })
    } catch (error) {
      setNotice({ tone: 'error', text: (error as Error).message })
    } finally {
      operationInProgress.current = false
      setRefreshingSource(false)
      setLoadingList(false)
      setLoadingWorkspace(false)
    }
  }

  return { compositions, selectedId, workspace, configuration, setConfiguration, baseline,
    query, setQuery, loadingList, loadingWorkspace, saving, bootstrapping, refreshingSource,
    notice, dirty, configuredCount, filteredCompositions, progress, weightTotal,
    selectComposition, changeComponentPriority, changeUnitCore, changeAugment, changeWeight,
    save, bootstrapAll, refreshSource }
}
