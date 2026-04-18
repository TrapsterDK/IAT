export type Side = "left" | "right";
export type KeyEventMode = "keydown" | "keyup";
export type StimulusContentType = "text" | "image";

export interface LandingTest {
  id: number;
  slug: string;
  title: string;
  description: string;
}

export interface TestListPayload {
  tests: LandingTest[];
}

export interface CategorySummary {
  id: number;
  code: string;
  label: string;
}

export interface StimulusSummary {
  id: number;
  contentType: StimulusContentType;
  textValue: string | null;
  assetPath: string | null;
}

export interface PhaseCategorySummary {
  id: number;
  label: string;
}

export interface PhaseSummary {
  id: number;
  sequenceNumber: number;
  showingsPerCategory: number;
  categories: {
    left: PhaseCategorySummary[];
    right: PhaseCategorySummary[];
  };
}

export interface VariantSummary {
  keyEventMode: KeyEventMode;
  keyboardShortcuts: {
    left: string;
    right: string;
  };
  preloadAssets: boolean;
  interTrialIntervalMs: number;
  responseTimeoutMs: number;
}

export interface TestPayload {
  attempt: {
    publicId: string;
    seed: number;
    attemptToken: string;
  };
  test: {
    slug: string;
    title: string;
    description: string;
  };
  variant: VariantSummary;
  categories: CategorySummary[];
  stimuliByCategory: Record<string, StimulusSummary[]>;
  phases: PhaseSummary[];
}

export interface PlannedShowing {
  phaseId: number;
  phaseIndex: number;
  showingIndex: number;
  stimulusId: number;
  stimulusLabel: string;
  stimulusAssetPath: string | null;
  expectedSide: Side;
  allowedLeftCategories: PhaseCategorySummary[];
  allowedRightCategories: PhaseCategorySummary[];
}

export interface ShowingInput {
  inputIndex: number;
  side: Side;
  inputSource: "keyboard" | "button";
  eventTimestampMs: number;
  handlerTimestampMs: number;
}

export interface ShowingResult {
  phaseId: number;
  stimulusId: number;
  showingIndex: number;
  stimulusOnsetMs: number;
  inputs: ShowingInput[];
}

export interface CompletionPayload {
  attemptToken: string;
  environment: {
    userAgent: string;
    platform: string;
    language: string;
    viewportWidth: number;
    viewportHeight: number;
    devicePixelRatio: number;
    visibilityInterruptions: number;
  };
  showings: ShowingResult[];
}

export interface AttemptSummary {
  showingCount: number;
  accuracy: number;
  meanInitialReactionTimeMs: number;
  meanCompletedReactionTimeMs: number;
  dscore: number;
}

export interface CompletionResult {
  attemptId: string;
  variant: string;
  summary: AttemptSummary;
}

declare global {
  interface Window {
    IAT_API_BASE_URL?: string;
  }
}
