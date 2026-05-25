import type { SessionMode } from "../state/types.mjs";

export interface FrontendStartupConfiguration {
  planSeed: number | null;
  sessionMode: SessionMode | null;
  startupError: string | null;
}

export function resolveStartupConfiguration(url: URL): FrontendStartupConfiguration {
  try {
    const planSeed = resolvePlanSeed(url);
    const sessionMode = resolveSessionMode(url);

    if (planSeed !== null && sessionMode === "participant") {
      throw new Error("Expected 'session_mode' to be 'evaluation' when 'plan_seed' is set.");
    }

    return {
      planSeed,
      sessionMode: sessionMode ?? (planSeed === null ? null : "evaluation"),
      startupError: null,
    };
  } catch (error: unknown) {
    return {
      planSeed: null,
      sessionMode: null,
      startupError: error instanceof Error ? error.message : "Unable to interpret startup query parameters.",
    };
  }
}

export function resolvePlanSeed(url: URL): number | null {
  const planSeed = readOptionalQueryParameter(url, "plan_seed");
  if (planSeed === null) {
    return null;
  }

  if (!/^\d+$/.test(planSeed)) {
    throw new Error("Expected one non-negative integer 'plan_seed' query parameter.");
  }

  const parsedPlanSeed = Number(planSeed);
  if (!Number.isSafeInteger(parsedPlanSeed)) {
    throw new Error("Expected one non-negative integer 'plan_seed' query parameter.");
  }

  return parsedPlanSeed;
}

export function resolveSessionMode(url: URL): SessionMode | null {
  const sessionMode = readOptionalQueryParameter(url, "session_mode");
  if (sessionMode === null) {
    return null;
  }

  if (sessionMode === "evaluation" || sessionMode === "participant") {
    return sessionMode;
  }

  throw new Error("Expected 'session_mode' to be 'participant' or 'evaluation'.");
}

function readOptionalQueryParameter(url: URL, parameterName: string) {
  const parameterValues = url.searchParams.getAll(parameterName);
  if (parameterValues.length > 1) {
    throw new Error(`Expected at most one '${parameterName}' query parameter.`);
  }

  return parameterValues[0]?.trim() ?? null;
}
