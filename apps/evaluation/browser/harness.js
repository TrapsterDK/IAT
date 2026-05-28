const BENCHMARK_NAMESPACE = "__iatEvaluation";
const AUTOMATION_EVENT_NAME = "iat:automation-state";
const AUTOMATION_NAMESPACE = "__iatAutomation";
const SESSION_STATES = ["block_intro", "catalog", "results", "review", "trial"];
const INPUT_MODES = ["keyboard", "touch"];
const RESPONSE_SIDES = ["left", "right"];
const ACTION_NAME_BY_RESPONSE_SIDE = {
  left: "respond-left",
  right: "respond-right",
};
const KEY_BY_RESPONSE_SIDE = {
  left: "e",
  right: "i",
};

(function registerEvaluationHarness(globalObject) {
  if (globalObject[BENCHMARK_NAMESPACE] !== undefined) {
    return;
  }

  globalObject[BENCHMARK_NAMESPACE] = {
    runBenchmark(config) {
      return executeBenchmark(globalObject, config);
    },
  };
})(window);

async function executeBenchmark(globalObject, config) {
  const runStartedAtPerfMs = globalObject.performance.now();
  const clickDelayMs = requireClickDelayMs(config.clickDelayMs);
  const sessionKeys = [];

  for (let sessionIndex = 0; sessionIndex < config.sessionCount; sessionIndex += 1) {
    sessionKeys.push(await runSession(clickDelayMs, config.iatSlug));
  }

  return {
    run_duration_ms: globalObject.performance.now() - runStartedAtPerfMs,
    session_keys: sessionKeys,
  };
}

async function runSession(clickDelayMs, iatSlug) {
  const snapshot = getAutomationSnapshot(true);
  if (snapshot?.sessionState === "results" && snapshot.pending !== true) {
    clickActionButton("back-to-catalog");
  }

  await waitForSessionState("catalog");

  startSession(iatSlug);
  const reviewSnapshot = await waitForSnapshot(
    (snapshot) => snapshot.sessionState === "review" && snapshot.sessionKey !== null,
  );
  const sessionKey = requireSessionKey(reviewSnapshot.sessionKey);

  await waitForReviewReadiness();
  beginTest();
  await waitForSessionState("block_intro");

  while (true) {
    const snapshot = getAutomationSnapshot();

    switch (snapshot.sessionState) {
      case "results":
        await waitForSnapshot(
          (nextSnapshot) => nextSnapshot.sessionState !== "results" || nextSnapshot.pending !== true,
        );
        return sessionKey;

      case "block_intro": {
        const blockSnapshot = await waitForBlockIntroReadiness();
        advanceBlockIntro(blockSnapshot.inputMode);
        await waitForSessionStateChange("block_intro");
        continue;
      }

      case "trial": {
        const blockIndex = requireTrialBlockIndex(snapshot.blockIndex);
        const trialIndex = requireTrialIndex(snapshot.trialIndex);
        const responseSide = requireTrialResponseSide(snapshot.correctResponseSide);
        const trialSnapshot = await waitForTrialReadiness(blockIndex, trialIndex);
        const remainingDelayMs = Math.max(
          0,
          clickDelayMs - (window.performance.now() - trialSnapshot.trialStartedAtMs),
        );

        await sleep(remainingDelayMs);
        dispatchAction(trialSnapshot.inputMode, responseSide);
        await waitForNextTrial(blockIndex, trialIndex);
        continue;
      }

      default:
        throw new Error(`Unexpected session state during benchmark run: ${snapshot.sessionState}`);
    }
  }
}

function dispatchAction(inputMode, responseSide) {
  if (inputMode === "touch") {
    clickActionButton(ACTION_NAME_BY_RESPONSE_SIDE[responseSide]);
    return;
  }

  dispatchKeyboardResponse(KEY_BY_RESPONSE_SIDE[responseSide]);
}

function waitForSessionState(expectedState) {
  return waitForSnapshot((snapshot) => snapshot.sessionState === expectedState);
}

function waitForSessionStateChange(previousState) {
  return waitForSnapshot((snapshot) => snapshot.sessionState !== previousState);
}

function waitForBlockIntroReadiness() {
  return waitForSnapshot((snapshot) => snapshot.sessionState === "block_intro" && snapshot.canAdvance);
}

function waitForReviewReadiness() {
  return waitForSnapshot((snapshot) => snapshot.sessionState === "review" && snapshot.canAdvance);
}

function waitForTrialReadiness(blockIndex, trialIndex) {
  return waitForSnapshot((snapshot) => {
    return (
      snapshot.sessionState === "trial" &&
      snapshot.blockIndex === blockIndex &&
      snapshot.trialIndex === trialIndex &&
      snapshot.trialStartedAtMs !== null
    );
  });
}

function waitForNextTrial(blockIndex, trialIndex) {
  return waitForSnapshot((snapshot) => {
    return (
      snapshot.sessionState !== "trial" || snapshot.blockIndex !== blockIndex || snapshot.trialIndex !== trialIndex
    );
  });
}

function waitForSnapshot(predicate) {
  return new Promise((resolve, reject) => {
    function cleanup() {
      window.removeEventListener(AUTOMATION_EVENT_NAME, handleAutomationEvent);
    }

    function resolveIfMatched(snapshot) {
      if (snapshot === null || !predicate(snapshot)) {
        return;
      }

      cleanup();
      resolve(snapshot);
    }

    function handleAutomationEvent(event) {
      try {
        resolveIfMatched(parseAutomationSnapshot(event.detail));
      } catch (error) {
        cleanup();
        reject(error);
      }
    }

    window.addEventListener(AUTOMATION_EVENT_NAME, handleAutomationEvent);

    try {
      resolveIfMatched(getAutomationSnapshot(true));
    } catch (error) {
      cleanup();
      reject(error);
    }
  });
}

function sleep(durationMs) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, durationMs);
  });
}

function requireClickDelayMs(clickDelayMs) {
  if (!Number.isInteger(clickDelayMs) || clickDelayMs < 0) {
    throw new Error("Expected one non-negative integer click delay.");
  }

  return clickDelayMs;
}

function requireSessionKey(sessionKey) {
  return requireNonBlankText(sessionKey, "Expected one non-blank created session key.");
}

function requireTrialResponseSide(responseSide) {
  if (responseSide === null) {
    throw new Error("Expected one trial automation correct-response side.");
  }

  return responseSide;
}

function startSession(iatSlug) {
  clickRequiredElement(`[data-action="start-session"][data-slug="${iatSlug}"]`);
}

function beginTest() {
  clickActionButton("begin-test");
}

function advanceBlockIntro(inputMode) {
  dispatchAction(inputMode, "left");
}

function clickActionButton(actionName) {
  clickRequiredElement(`[data-action="${actionName}"]`);
}

function clickRequiredElement(selector) {
  const element = document.querySelector(selector);
  if (!(element instanceof HTMLElement)) {
    throw new Error(`Expected one DOM element matching '${selector}'.`);
  }

  element.click();
}

function dispatchKeyboardResponse(key) {
  const keyboardEvent = new KeyboardEvent("keydown", {
    bubbles: true,
    cancelable: true,
    key,
  });
  document.dispatchEvent(keyboardEvent);
}

function getAutomationSnapshot(allowMissing = false) {
  const publishedSnapshot = window[AUTOMATION_NAMESPACE];
  if (publishedSnapshot === undefined) {
    if (allowMissing) {
      return null;
    }

    throw new Error("Expected one published automation snapshot.");
  }

  return parseAutomationSnapshot(publishedSnapshot);
}

function requireTrialBlockIndex(blockIndex) {
  if (typeof blockIndex !== "number") {
    throw new Error("Expected one active trial snapshot with one numeric block index.");
  }

  return blockIndex;
}

function requireTrialIndex(trialIndex) {
  if (typeof trialIndex !== "number") {
    throw new Error("Expected one active trial snapshot with one numeric trial index.");
  }

  return trialIndex;
}

function parseAutomationSnapshot(rawSnapshot) {
  if (typeof rawSnapshot !== "object" || rawSnapshot === null) {
    throw new Error("Expected one published automation snapshot object.");
  }

  return {
    blockIndex: parseOptional(rawSnapshot.blockIndex, parseInteger),
    canAdvance: parseBoolean(rawSnapshot.canAdvance),
    correctResponseSide: parseOptional(rawSnapshot.correctResponseSide, parseCorrectResponseSide),
    inputMode: parseInputMode(rawSnapshot.inputMode),
    iatSlug: parseOptional(rawSnapshot.iatSlug, parseAutomationText),
    pending: parseBoolean(rawSnapshot.pending),
    sessionKey: parseOptional(rawSnapshot.sessionKey, parseAutomationText),
    sessionState: parseSessionState(rawSnapshot.sessionState),
    trialStartedAtMs: parseOptional(rawSnapshot.trialStartedAtMs, parseNumber),
    trialIndex: parseOptional(rawSnapshot.trialIndex, parseInteger),
  };
}

function parseInteger(rawValue) {
  if (!Number.isInteger(rawValue) || rawValue < 0) {
    throw new Error(`Expected one non-negative integer automation value, received '${rawValue}'.`);
  }

  return rawValue;
}

function parseNumber(rawValue) {
  if (typeof rawValue !== "number" || !Number.isFinite(rawValue) || rawValue < 0) {
    throw new Error(`Expected one non-negative numeric automation value, received '${rawValue}'.`);
  }

  return rawValue;
}

function parseBoolean(rawValue) {
  if (typeof rawValue !== "boolean") {
    throw new Error(`Expected one boolean automation value, received '${rawValue}'.`);
  }

  return rawValue;
}

function parseSessionState(rawValue) {
  return requireSupportedValue(rawValue, SESSION_STATES, "Expected one supported published automation session state.");
}

function parseInputMode(rawValue) {
  return requireSupportedValue(rawValue, INPUT_MODES, "Expected one supported published automation input mode.");
}

function parseCorrectResponseSide(rawValue) {
  return requireSupportedValue(
    rawValue,
    RESPONSE_SIDES,
    `Expected one supported correct-response side, received '${rawValue}'.`,
  );
}

function parseAutomationText(rawValue) {
  return requireNonBlankText(rawValue, `Expected one non-blank automation text value, received '${rawValue}'.`);
}

function parseOptional(rawValue, parseValue) {
  if (rawValue === undefined || rawValue === null) {
    return null;
  }

  return parseValue(rawValue);
}

function requireSupportedValue(rawValue, supportedValues, errorMessage) {
  if (!supportedValues.includes(rawValue)) {
    throw new Error(errorMessage);
  }

  return rawValue;
}

function requireNonBlankText(rawValue, errorMessage) {
  if (typeof rawValue !== "string" || rawValue.trim() === "") {
    throw new Error(errorMessage);
  }

  return rawValue;
}
