import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../testing/fixtures.mjs";
import { buildAutomationSnapshot } from "./automation.mjs";
import { beginTrial } from "./states/block_intro.mjs";
import { beginBlockIntro, createSessionState } from "./states/review.mjs";
import { ResponseSide, SessionStateKind, type ResultSessionState, type RuntimeState } from "./types.mjs";

test("buildAutomationSnapshot describes one touch-first catalog state without one active session", () => {
  // Given: one runtime has no active session and prefers touch input.
  const runtime = createRuntimeFixture(true);

  // When: the benchmark automation snapshot is built.
  const snapshot = buildAutomationSnapshot(runtime);

  // Then: the snapshot reports one catalog state with no active-session metadata.
  assert.deepEqual(snapshot, {
    blockIndex: null,
    canAdvance: false,
    correctResponseSide: null,
    iatSlug: null,
    inputMode: "touch",
    pending: false,
    sessionKey: null,
    sessionState: "catalog",
    trialIndex: null,
    trialStartedAtMs: null,
  });
});

test("buildAutomationSnapshot describes one ready review state after preloading completes", () => {
  // Given: one runtime is reviewing a fully prepared session.
  const runtime = createRuntimeFixture(false);
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  reviewSession.preload.loaded = reviewSession.preload.total;
  runtime.session = reviewSession;

  // When: the benchmark automation snapshot is built.
  const snapshot = buildAutomationSnapshot(runtime);

  // Then: the snapshot reports that the review can advance.
  assert.deepEqual(snapshot, {
    blockIndex: null,
    canAdvance: true,
    correctResponseSide: null,
    iatSlug: "sample-iat",
    inputMode: "keyboard",
    pending: false,
    sessionKey: "session-1",
    sessionState: "review",
    trialIndex: null,
    trialStartedAtMs: null,
  });
});

test("buildAutomationSnapshot describes one ready trial with one correct response side", () => {
  // Given: one runtime is on the first trial of one keyboard-driven session.
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  reviewSession.preload.loaded = reviewSession.preload.total;
  const trialSession = beginTrial(beginBlockIntro(reviewSession));
  trialSession.trial.startedAtMs = 1234;
  const runtime = createRuntimeFixture(false);
  runtime.session = trialSession;

  // When: the benchmark automation snapshot is built.
  const snapshot = buildAutomationSnapshot(runtime);

  // Then: the snapshot reports the active trial metadata needed by the harness.
  assert.deepEqual(snapshot, {
    blockIndex: 0,
    canAdvance: false,
    correctResponseSide: "left",
    iatSlug: "sample-iat",
    inputMode: "keyboard",
    pending: false,
    sessionKey: "session-1",
    sessionState: "trial",
    trialIndex: 0,
    trialStartedAtMs: 1234,
  });
});

test("buildAutomationSnapshot clears trial metadata after one session reaches results", () => {
  // Given: one runtime has already stored one completed-session result.
  const resultSession: ResultSessionState = {
    bootstrap: createBootstrapFixture(),
    iatDetail: createIatDetailFixture(),
    pending: false,
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
    canAdvance: false,
    correctResponseSide: null,
    iatSlug: "sample-iat",
    inputMode: "keyboard",
    pending: false,
    sessionKey: "session-1",
    sessionState: "results",
    trialIndex: null,
    trialStartedAtMs: null,
  });
});

test("buildAutomationSnapshot reports when one block intro is waiting for uploads", () => {
  // Given: one runtime has reached the next block intro while the previous block is still unsaved.
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  reviewSession.preload.loaded = reviewSession.preload.total;
  const blockIntroSession = beginBlockIntro(reviewSession);
  blockIntroSession.blockUpload.pendingUpload = {
    blockIndex: 1,
    payload: { trials: [{ events: [{ elapsedMs: 30, eventType: ResponseSide.Left }] }] },
  };
  const runtime = createRuntimeFixture(false);
  runtime.session = blockIntroSession;

  // When: the benchmark automation snapshot is built.
  const snapshot = buildAutomationSnapshot(runtime);

  // Then: the snapshot keeps the block intro visible but marks it as not startable.
  assert.equal(snapshot.sessionState, "block_intro");
  assert.equal(snapshot.blockIndex, 0);
  assert.equal(snapshot.canAdvance, false);
});

test("buildAutomationSnapshot reports when one block intro can begin", () => {
  // Given: one runtime has reached a block intro with no pending uploads.
  const runtime = createRuntimeFixture(false);
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  reviewSession.preload.loaded = reviewSession.preload.total;
  runtime.session = beginBlockIntro(reviewSession);

  // When: the benchmark automation snapshot is built.
  const snapshot = buildAutomationSnapshot(runtime);

  // Then: the snapshot marks the block intro as startable.
  assert.equal(snapshot.sessionState, "block_intro");
  assert.equal(snapshot.blockIndex, 0);
  assert.equal(snapshot.canAdvance, true);
});

test("buildAutomationSnapshot reports when one block intro is visibly starting", () => {
  // Given: one runtime has started the visible one-second block delay.
  const runtime = createRuntimeFixture(false);
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  reviewSession.preload.loaded = reviewSession.preload.total;
  const blockIntroSession = beginBlockIntro(reviewSession);
  blockIntroSession.starting = true;
  runtime.session = blockIntroSession;

  // When: the benchmark automation snapshot is built.
  const snapshot = buildAutomationSnapshot(runtime);

  // Then: the block intro stays published but cannot advance during the delay.
  assert.equal(snapshot.sessionState, "block_intro");
  assert.equal(snapshot.blockIndex, 0);
  assert.equal(snapshot.canAdvance, false);
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
