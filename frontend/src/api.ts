// API client functions
// In dev: /api is proxied by Vite to backend (see vite.config.ts)
// In production: VITE_API_URL points to the deployed backend (e.g. Render)
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

/** Derive context level from clinic (optedIn + contributionPct). Matches backend logic. */
export function getContextLevelFromClinic(clinic: { optedIn: boolean; contributionPct: number }): number {
  if (!clinic.optedIn || clinic.contributionPct < 10) return 0
  if (clinic.contributionPct < 40) return 1
  if (clinic.contributionPct < 80) return 2
  return 3
}

/** Derive network status from context level. 0→Isolated, 1→Basic, 2→Collaborative, 3→Trusted Contributor. */
export function getNetworkStatusFromLevel(contextLevel: number): string {
  const map: Record<number, string> = {
    0: 'Isolated',
    1: 'Basic',
    2: 'Collaborative',
    3: 'Trusted Contributor',
  }
  return map[contextLevel] ?? 'Isolated'
}

export interface Clinic {
  clinicId: string
  name: string
  optedIn: boolean
  contributionPct: number
  contextLevel: number
  networkStatus: string
}

export interface IntakeCheckRequest {
  clinicId: string
  fullName: string
  dob: string
  phoneLast4: string
}

export interface ContributingClinic {
  clinicId: string
  clinicName: string
  contributorLevel: number
  visibleLevel: number
  isCapped: boolean
  networkStatus?: string
}

export interface WhatIfScenario {
  targetPct: number
  targetLevel: number
  unlocks: string[]
  increaseNeeded: number
}

export interface IntakeCheckResponse {
  matchFound: boolean
  fingerprint: string
  requestingClinic: {
    clinicId: string
    optedIn: boolean
    contributionPct: number
    contextLevel: number
  }
  networkStats: {
    participatingClinicsCount: number
    participatingClinicsPct: number
  }
  contributionGating: {
    contributingClinicsCount: number
    detailCappedClinicsCount: number
    contributingClinics: ContributingClinic[]
    reason: string
  }
  sharedSummary: any | null
  lockedPreview: {
    nextLevelUnlocks: string[]
  }
  whatIf: WhatIfScenario[]
}

export async function fetchClinics(): Promise<Clinic[]> {
  const url = `${API_BASE_URL}/clinics`
  try {
    const response = await fetch(url)
    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Failed to fetch clinics (${response.status}): ${text || response.statusText}`)
    }
    return response.json()
  } catch (err) {
    if (err instanceof TypeError && err.message === 'Failed to fetch') {
      throw new Error('Failed to load clinics. Is the backend running? (cd heidi-prototype/backend && uvicorn main:app --reload)')
    }
    throw err
  }
}

export async function updateClinicSettings(
  clinicId: string,
  optedIn: boolean,
  contributionPct: number
): Promise<Clinic> {
  const response = await fetch(`${API_BASE_URL}/clinics/${clinicId}/settings`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      optedIn,
      contributionPct,
    }),
  })
  if (!response.ok) {
    const errorText = await response.text()
    let errorMessage = 'Failed to update clinic settings'
    try {
      const errorJson = JSON.parse(errorText)
      errorMessage = errorJson.detail || errorMessage
    } catch {
      errorMessage = errorText || errorMessage
    }
    throw new Error(errorMessage)
  }
  return response.json()
}

export async function checkIntake(
  request: IntakeCheckRequest
): Promise<IntakeCheckResponse> {
  const response = await fetch(`${API_BASE_URL}/intake/check`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    throw new Error('Failed to check intake')
  }
  return response.json()
}

export interface ContinueCareRequest {
  clinicId: string
  fullName: string
  dob: string
  phoneLast4: string
}

export interface ContinueCareResponse {
  status: 'recorded' | 'already_recorded' | 'no_contributors'
  credited: boolean
  creditsAwarded: number
  message: string
  events: Array<{ patientId: string; fromClinic: string; toClinic: string; timestamp: string }>
}

export async function continueCare(request: ContinueCareRequest): Promise<ContinueCareResponse> {
  const url = `${API_BASE_URL}/intake/continue-care`
  if (import.meta.env.DEV) {
    console.log('[Continue Care] POST', url, 'body:', request)
  }
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  const bodyText = await response.text()
  if (import.meta.env.DEV) {
    console.log('[Continue Care]', response.status, bodyText)
  }
  if (!response.ok) {
    let errorMessage: string
    if (response.status === 404) {
      errorMessage = `404: Continue Care endpoint not found. Check backend is running on port 8000.`
      try {
        const errJson = JSON.parse(bodyText)
        if (errJson.detail && typeof errJson.detail === 'string') {
          errorMessage = `${response.status}: ${errJson.detail}`
        }
      } catch {
        // keep generic
      }
    } else {
      errorMessage = `Continue care failed (${response.status})`
      try {
        const errJson = JSON.parse(bodyText)
        const detail = errJson.detail
        const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ') : bodyText
        errorMessage = msg ? `${response.status}: ${msg}` : errorMessage
      } catch {
        errorMessage = bodyText ? `${response.status}: ${bodyText}` : errorMessage
      }
    }
    throw new Error(errorMessage)
  }
  return JSON.parse(bodyText) as ContinueCareResponse
}

export interface CreditsDashboard {
  clinicCredits: Record<string, number>
  recentEvents: Array<{ patientId: string; fromClinic: string; toClinic: string; timestamp: string }>
}

export async function fetchCreditsDashboard(): Promise<CreditsDashboard> {
  const response = await fetch(`${API_BASE_URL}/credits/dashboard`)
  if (!response.ok) throw new Error('Failed to fetch credits dashboard')
  return response.json()
}

export interface ClinicBenchmark {
  eligible: boolean
  reason?: string | null
  clinicDistribution: { improving: number; plateau: number; worse: number }
  networkAverage: { improving: number; plateau: number; worse: number }
  participating_count?: number
}

export async function fetchClinicBenchmark(clinicId: string): Promise<ClinicBenchmark> {
  const response = await fetch(`${API_BASE_URL}/clinics/${clinicId}/benchmark`)
  if (!response.ok) throw new Error('Failed to fetch benchmark')
  return response.json()
}

/** Demo mode status (for reviewer tools visibility). */
export async function fetchDemoStatus(): Promise<{ demoMode: boolean }> {
  try {
    const response = await fetch(`${API_BASE_URL}/demo/status`)
    if (!response.ok) return { demoMode: false }
    return response.json()
  } catch {
    return { demoMode: false }
  }
}

/** Set all clinics to Level 0 (demo scenario). Only available when backend DEMO_MODE=true. */
export async function demoScenarioAllLevel0(): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/demo/scenario/all_level_0`, { method: 'POST' })
  if (!response.ok) {
    const text = await response.text()
    let detail = 'Scenario failed'
    try {
      const j = JSON.parse(text)
      if (j.detail) detail = j.detail
    } catch {
      detail = text || `HTTP ${response.status}`
    }
    throw new Error(`${response.status}: ${detail}`)
  }
  return response.json()
}

/** Reset demo data. Only available when backend DEMO_MODE=true. */
export async function demoReset(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/demo/reset`, { method: 'POST' })
  if (!response.ok) {
    const text = await response.text()
    let detail = 'Reset failed'
    try {
      const j = JSON.parse(text)
      if (j.detail) detail = j.detail
    } catch {
      detail = text || `HTTP ${response.status}`
    }
    throw new Error(`${response.status}: ${detail}`)
  }
  return response.json()
}
