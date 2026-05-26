import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../testing/fixtures.mjs";
import { buildAutomationSnapshot } from "./automation.mjs";
import { beginStartingBlock } from "./states/block_intro.mjs";
import { beginBlockIntro } from "./states/preloading.mjs";
import { beginPreloading, createSessionState } from "./states/review.mjs";
import { beginTrial } from "./states/starting_block.mjs";
import { SessionStateKind, type ResultSessionState, type RuntimeState } from "./types.mjs";

test("buildAutomationSnapshot describes one touch-first catalog state without one active session", () => {
  // Given: one runtime has no active session and prefers touch input.
  const runtime = createRuntimeFixture(true);

  // When: the benchmark automation snapshot is built.
  const snapshot = buildAutomationSnapshot(runtime);

  // Then: the snapshot reports one catalog state with no active-session metadata.
  assert.deepEqual(snapshot, {
    blockIndex: null,
    correctResponseSide: null,
    iatSlug: null,
    inputMode: "touch",
    sessionKey: null,
    sessionState: "catalog",
    trialIndex: null,
    trialStartedAtMs: null,
  });
});

test("buildAutomationSnapshot describes one ready trial with one correct response side", () => {
  // Given: one runtime is on the first trial of one keyboard-driven session.
  const trialSession = beginTrial(
    beginStartingBlock(
      beginBlockIntro(beginPreloading(createSessionState(createIatDetailFixture(), createBootstrapFixture()))),
    ),
  );
  trialSession.trial.startedAtMs = 1234;
  const runtime = createRuntimeFixture(false);
  runtime.session = trialSession;

  // When: the benchmark automation snapshot is built.
  const snapshot = buildAutomationSnapshot(runtime);

  // Then: the snapshot reports the active trial metadata needed by the harness.
  assert.deepEqual(snapshot, {
    blockIndex: 0,
    correctResponseSide: "left",
    iatSlug: "sample-iat",
    inputMode: "keyboard",
    sessionKey: "session-1",
    sessionState: "trial",
    trialIndex: 0,
    trialStartedAtMs: 1234,
  });
});

test("buildAutomationSnapshot clears trial metadata after one session reaches results", () => {
  // Given: one runtime has already stored one completed-session result.
  const resultSession: ResultSessionState = {
    ...createSessionState(createIatDetailFixture(), createBootstrapFixture()),
    result: {
      score: null,
      scoreError: "Result unavailable.",
    },
    state: SessionStateKind.Results,
  };
  const runtime = createRuntimeFixture(false);
  runtime.session = resultSession;

  // When: the benchmark automation snapshot is built.
  const snapshot = buildAutomationSnapshot(runtime);

  // Then: the snapshot keeps session identity but drops active-stage metadata.
  assert.deepEqual(snapshot, {
    blockIndex: null,
    correctResponseSide: null,
    iatSlug: "sample-iat",
    inputMode: "keyboard",
    sessionKey: "session-1",
    sessionState: "results",
    trialIndex: null,
    trialStartedAtMs: null,
  });
});

function createRuntimeFixture(prefersTouchInput: boolean): RuntimeState {
  return {
    assets: {
      imageObjectUrls: new Map(),
    },
    catalog: {
      error: null,
      items: [],
      loading: false,
      startingIatSlug: null,
    },
    device: {
      prefersTouchInput,
    },
    session: null,
    ui: {
      screenError: null,
    },
  };
}
