// TypeScript type definitions - EXACT spec

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
  dob: string // YYYY-MM-DD
  phoneLast4: string
}

export interface SharedSummary {
  conditions?: string[]
  dateRanges?: Array<{ start: string; end: string }>
  contributingClinicsCount?: number
  interventions?: string[]
  responseTrend?: string
  redFlags?: string[]
  timeline?: string[]
  lastSeenDate?: string
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
  sharedSummary: SharedSummary | null
  lockedPreview: {
    nextLevelUnlocks: string[]
  }
  whatIf: WhatIfScenario[]
}
