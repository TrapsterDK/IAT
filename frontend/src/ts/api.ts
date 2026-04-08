import type {
  CategorySummary,
  CompletionResult,
  LandingTest,
  PhaseCategorySummary,
  PhaseSummary,
  StimulusSummary,
  TestListPayload,
  TestPayload,
  AttemptSummary,
  VariantSummary,
} from "./types";

const DEFAULT_LOCAL_API_BASE_URL = "http://127.0.0.1:8000/api";
export const API_REQUEST_TIMEOUT_MS = 10_000;

interface FetchErrorMessages {
  timeout?: string;
  network?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isBoolean(value: unknown): value is boolean {
  return typeof value === "boolean";
}

function isAbortError(error: unknown): boolean {
  return typeof error === "object" && error !== null && "name" in error && error.name === "AbortError";
}

function isLandingTest(value: unknown): value is LandingTest {
  return (
    isRecord(value) &&
    isNumber(value.id) &&
    isString(value.slug) &&
    isString(value.title) &&
    isString(value.description)
  );
}

function isCategorySummary(value: unknown): value is CategorySummary {
  return isRecord(value) && isNumber(value.id) && isString(value.code) && isString(value.label);
}

function isStimulusSummary(value: unknown): value is StimulusSummary {
  if (!isRecord(value) || !isNumber(value.id)) {
    return false;
  }

  if (value.contentType === "text") {
    return isString(value.textValue) && value.textValue.length > 0 && value.assetPath === null;
  }

  if (value.contentType === "image") {
    return isString(value.assetPath) && value.assetPath.length > 0 && value.textValue === null;
  }

  return false;
}

function isPhaseCategorySummary(value: unknown): value is PhaseCategorySummary {
  return isRecord(value) && isNumber(value.id) && isString(value.label);
}

function isPhaseSummary(value: unknown): value is PhaseSummary {
  return (
    isRecord(value) &&
    isNumber(value.id) &&
    isNumber(value.sequenceNumber) &&
    value.sequenceNumber > 0 &&
    isNumber(value.showingsPerCategory) &&
    value.showingsPerCategory > 0 &&
    isRecord(value.categories) &&
    Array.isArray(value.categories.left) &&
    value.categories.left.every(isPhaseCategorySummary) &&
    Array.isArray(value.categories.right) &&
    value.categories.right.every(isPhaseCategorySummary)
  );
}

function isVariantSummary(value: unknown): value is VariantSummary {
  return (
    isRecord(value) &&
    (value.keyEventMode === "keydown" || value.keyEventMode === "keyup") &&
    isRecord(value.keyboardShortcuts) &&
    isString(value.keyboardShortcuts.left) &&
    value.keyboardShortcuts.left.length > 0 &&
    isString(value.keyboardShortcuts.right) &&
    value.keyboardShortcuts.right.length > 0 &&
    isBoolean(value.preloadAssets) &&
    isNumber(value.interTrialIntervalMs) &&
    value.interTrialIntervalMs >= 0 &&
    isNumber(value.responseTimeoutMs) &&
    value.responseTimeoutMs > 0
  );
}

function isStimuliByCategory(value: unknown): value is Record<string, StimulusSummary[]> {
  return (
    isRecord(value) &&
    Object.values(value).every((stimuli) => Array.isArray(stimuli) && stimuli.every(isStimulusSummary))
  );
}

function isTestPayload(value: unknown): value is TestPayload {
  return (
    isRecord(value) &&
    isRecord(value.attempt) &&
    isString(value.attempt.publicId) &&
    isNumber(value.attempt.seed) &&
    isString(value.attempt.attemptToken) &&
    isRecord(value.test) &&
    isString(value.test.slug) &&
    isString(value.test.title) &&
    isString(value.test.description) &&
    isVariantSummary(value.variant) &&
    Array.isArray(value.categories) &&
    value.categories.every(isCategorySummary) &&
    isStimuliByCategory(value.stimuliByCategory) &&
    Array.isArray(value.phases) &&
    value.phases.every(isPhaseSummary)
  );
}

function isTestListPayload(value: unknown): value is TestListPayload {
  return isRecord(value) && Array.isArray(value.tests) && value.tests.every(isLandingTest);
}

function isAttemptSummary(value: unknown): value is AttemptSummary {
  return (
    isRecord(value) &&
    isNumber(value.showingCount) &&
    isNumber(value.accuracy) &&
    isNumber(value.meanInitialReactionTimeMs) &&
    isNumber(value.meanCompletedReactionTimeMs)
  );
}

function isCompletionResult(value: unknown): value is CompletionResult {
  return isRecord(value) && isString(value.attemptId) && isString(value.variant) && isAttemptSummary(value.summary);
}

export function apiBaseUrl(): string {
  if (typeof window === "undefined") {
    return DEFAULT_LOCAL_API_BASE_URL;
  }

  if (typeof window.IAT_API_BASE_URL === "string" && window.IAT_API_BASE_URL.trim().length > 0) {
    return new URL(window.IAT_API_BASE_URL, window.location.origin).toString().replace(/\/$/, "");
  }

  return new URL("/api", window.location.origin).toString();
}

export async function fetchWithTimeout(
  input: RequestInfo | URL,
  init?: RequestInit,
  messages: FetchErrorMessages = {},
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => {
    controller.abort();
  }, API_REQUEST_TIMEOUT_MS);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (isAbortError(error)) {
      throw new Error(
        messages.timeout ?? `The server did not respond within ${API_REQUEST_TIMEOUT_MS / 1000} seconds.`,
      );
    }
    throw new Error(messages.network ?? "Could not reach the server.");
  } finally {
    globalThis.clearTimeout(timeoutId);
  }
}

export function parseTestListPayload(value: unknown): TestListPayload {
  if (!isTestListPayload(value)) {
    throw new Error("Invalid test list response.");
  }
  return value;
}

export function parseTestPayload(value: unknown): TestPayload {
  if (!isTestPayload(value)) {
    throw new Error("Invalid test payload.");
  }
  return value;
}

export function parseCompletionResult(value: unknown): CompletionResult {
  if (!isCompletionResult(value)) {
    throw new Error("Invalid completion response.");
  }
  return value;
}
