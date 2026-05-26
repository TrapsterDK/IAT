import { buildAutomationSnapshot, type AutomationSnapshot } from "./state/automation.mjs";
import type { RuntimeState } from "./state/types.mjs";

const AUTOMATION_NAMESPACE = "__iatAutomation" as const;
const AUTOMATION_EVENT_NAME = "iat:automation-state";

declare global {
  interface Window {
    __iatAutomation?: AutomationSnapshot;
  }
}

export function publishAutomationSnapshot(globalObject: Window, runtime: RuntimeState) {
  const snapshot = buildAutomationSnapshot(runtime);
  const previousSnapshot = globalObject[AUTOMATION_NAMESPACE];
  if (
    previousSnapshot !== undefined &&
    previousSnapshot.blockIndex === snapshot.blockIndex &&
    previousSnapshot.correctResponseSide === snapshot.correctResponseSide &&
    previousSnapshot.iatSlug === snapshot.iatSlug &&
    previousSnapshot.inputMode === snapshot.inputMode &&
    previousSnapshot.sessionKey === snapshot.sessionKey &&
    previousSnapshot.sessionState === snapshot.sessionState &&
    previousSnapshot.trialIndex === snapshot.trialIndex &&
    previousSnapshot.trialStartedAtMs === snapshot.trialStartedAtMs
  ) {
    return;
  }

  globalObject[AUTOMATION_NAMESPACE] = snapshot;
  globalObject.dispatchEvent(
    new CustomEvent(AUTOMATION_EVENT_NAME, {
      detail: snapshot,
    }),
  );
}
