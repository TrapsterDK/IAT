import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../../testing/fixtures.mjs";
import { canAdvanceSession } from "../block_uploads.mjs";
import { beginTrial } from "./block_intro.mjs";
import { beginBlockIntro, createSessionState } from "./review.mjs";
import { advanceSessionAfterCompletedTrial, registerTrialResponse } from "./trial.mjs";
import { ResponseSide, SessionStateKind, TrialAdvanceKind, TrialResponseKind } from "../types.mjs";

test("registerTrialResponse ignores input after the trial has locked", () => {
  // Given: one active trial session has already accepted its correct response.
  const trialSession = createTrialSession();
  trialSession.trial.activeEvents = [{ elapsedMs: 20, eventType: ResponseSide.Right }];
  trialSession.trial.responseLocked = true;

  // When: another response is registered after the lock is active.
  const responseResult = registerTrialResponse(trialSession, ResponseSide.Left, 45);

  // Then: the response is ignored and the existing trial events stay unchanged.
  assert.equal(responseResult.kind, TrialResponseKind.Ignored);
  assert.deepEqual(trialSession.trial.activeEvents, [{ elapsedMs: 20, eventType: ResponseSide.Right }]);
});

test("registerTrialResponse returns incorrect when the response side does not match", () => {
  // Given: one active trial session expects a left-side response for the current trial.
  const trialSession = createTrialSession();

  // When: an incorrect response side is entered.
  const responseResult = registerTrialResponse(trialSession, ResponseSide.Right, 45);

  // Then: the response is recorded as incorrect and the trial stays unlocked.
  assert.equal(responseResult.kind, TrialResponseKind.Incorrect);
  assert.deepEqual(trialSession.trial.activeEvents, [{ elapsedMs: 45, eventType: ResponseSide.Right }]);
  assert.equal(trialSession.trial.responseLocked, false);
});

test("registerTrialResponse accepts the correct response and clears active events", () => {
  // Given: one active trial session has already recorded one incorrect response.
  const trialSession = createTrialSession();
  trialSession.trial.activeEvents = [{ elapsedMs: 20, eventType: ResponseSide.Right }];

  // When: the correct side is entered for the current trial.
  const responseResult = registerTrialResponse(trialSession, ResponseSide.Left, 55);

  // Then: the completed trial is returned and the session locks until advancement.
  assert.equal(responseResult.kind, TrialResponseKind.Accepted);
  assert.deepEqual(responseResult.completedTrial, {
    events: [
      { elapsedMs: 20, eventType: ResponseSide.Right },
      { elapsedMs: 55, eventType: ResponseSide.Left },
    ],
  });
  assert.deepEqual(trialSession.trial.activeEvents, []);
  assert.equal(trialSession.trial.responseLocked, true);
});

test("advanceSessionAfterCompletedTrial advances to the next trial inside the same block", () => {
  // Given: one trial session is in a block that still has another trial remaining.
  const trialSession = createTrialSession(createBootstrapWithTrialCounts([2]));
  const completedTrial = {
    events: [{ elapsedMs: 40, eventType: ResponseSide.Left }],
  };

  // When: the first trial is completed.
  const advanceResult = advanceSessionAfterCompletedTrial(trialSession, completedTrial);

  // Then: the session stays in the trial stage and starts the next trial immediately.
  assert.equal(advanceResult.kind, TrialAdvanceKind.AdvancedTrial);
  assert.equal(advanceResult.session.state, SessionStateKind.Trial);
  assert.equal(advanceResult.session.currentBlockIndex, 0);
  assert.equal(advanceResult.session.currentTrialIndex, 1);
  assert.deepEqual(advanceResult.session.currentBlockTrials, [completedTrial]);
  assert.deepEqual(advanceResult.session.trial.activeEvents, []);
  assert.equal(advanceResult.session.trial.responseLocked, false);
  assert.equal(advanceResult.session.trial.startedAtMs, null);
});

test("registerTrialResponse ignores input before presentation is ready", () => {
  // Given: one active trial session has not finished its presentation-ready handshake.
  const trialSession = createTrialSession();
  trialSession.trial.startedAtMs = null;

  // When: one response is registered before the trial is ready.
  const responseResult = registerTrialResponse(trialSession, ResponseSide.Left, 45);

  // Then: the response is ignored and no trial events are recorded yet.
  assert.equal(responseResult.kind, TrialResponseKind.Ignored);
  assert.deepEqual(trialSession.trial.activeEvents, []);
  assert.equal(trialSession.trial.responseLocked, false);
});

test("advanceSessionAfterCompletedTrial advances to the next block after the final trial", () => {
  // Given: one trial session is on the last trial of a non-final block.
  const trialSession = createTrialSession(createBootstrapWithTrialCounts([1, 1]));
  const completedTrial = {
    events: [{ elapsedMs: 65, eventType: ResponseSide.Left }],
  };

  // When: the block's final trial is completed.
  const advanceResult = advanceSessionAfterCompletedTrial(trialSession, completedTrial);

  // Then: the next block intro is shown but blocked until the finished block is uploaded.
  assert.equal(advanceResult.kind, TrialAdvanceKind.AdvancedBlock);
  assert.equal(advanceResult.session.state, SessionStateKind.BlockIntro);
  assert.equal(advanceResult.session.currentBlockIndex, 1);
  assert.equal(advanceResult.session.starting, false);
  assert.equal(canAdvanceSession(advanceResult.session), false);
  assert.deepEqual(advanceResult.session.blockUpload.pendingUpload, {
    blockIndex: 1,
    payload: { trials: [completedTrial] },
  });
  assert.equal(advanceResult.session.blockUpload.uploadError, null);
});

test("advanceSessionAfterCompletedTrial enters pending results after the last block completes", () => {
  // Given: one trial session is on the final trial of the final block.
  const trialSession = createTrialSession(createBootstrapWithTrialCounts([1]));
  const completedTrial = {
    events: [{ elapsedMs: 90, eventType: ResponseSide.Left }],
  };

  // When: the session completes its last remaining trial.
  const advanceResult = advanceSessionAfterCompletedTrial(trialSession, completedTrial);

  // Then: the session enters results in its pending phase with one pending block upload.
  assert.equal(advanceResult.kind, TrialAdvanceKind.AdvancedResult);
  assert.equal(advanceResult.session.state, SessionStateKind.Results);
  assert.equal(advanceResult.session.pending, true);
  assert.deepEqual(advanceResult.session.blockUpload.pendingUpload, {
    blockIndex: 1,
    payload: { trials: [completedTrial] },
  });
  assert.equal(advanceResult.session.blockUpload.uploadError, null);
  assert.deepEqual(advanceResult.session.result, {
    score: null,
    scoreError: null,
  });
});

test("advanceSessionAfterCompletedTrial returns ignored when no current block exists", () => {
  // Given: one trial session points beyond the available block indexes.
  const trialSession = {
    ...createTrialSession(),
    currentBlockIndex: 1,
  };
  const completedTrial = {
    events: [{ elapsedMs: 90, eventType: ResponseSide.Left }],
  };

  // When: advancement is attempted without an active block.
  const advanceResult = advanceSessionAfterCompletedTrial(trialSession, completedTrial);

  // Then: the session is returned unchanged with an ignored advance result.
  assert.equal(advanceResult.kind, TrialAdvanceKind.Ignored);
  assert.equal(advanceResult.session, trialSession);
});

function createTrialSession(bootstrap = createBootstrapFixture()) {
  const reviewSession = createSessionState(createIatDetailFixture(), bootstrap);
  reviewSession.preload.loaded = reviewSession.preload.total;
  const trialSession = beginTrial(beginBlockIntro(reviewSession));

  trialSession.trial.startedAtMs = 10;
  return trialSession;
}

function createBootstrapWithTrialCounts(trialCounts: number[]) {
  const bootstrap = createBootstrapFixture();
  const baseBlock = bootstrap.blocks[0];
  const baseTrial = baseBlock?.trials[0];
  if (baseBlock === undefined || baseTrial === undefined) {
    throw new Error("Expected one base block and trial fixture.");
  }

  return {
    ...bootstrap,
    blocks: trialCounts.map((trialCount, blockIndex) => ({
      ...baseBlock,
      is_practice: blockIndex === 0,
      trials: Array.from({ length: trialCount }, (_value, trialIndex) => ({
        ...baseTrial,
        stimulus: {
          image_url: null,
          text: `stimulus-${blockIndex}-${trialIndex}`,
        },
      })),
    })),
  };
}
