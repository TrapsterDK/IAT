import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../../testing/fixtures.mjs";
import { beginStartingBlock, beginTrial } from "./block_intro.mjs";
import { beginBlockIntro, createSessionState } from "./review.mjs";
import { SessionStateKind } from "../types.mjs";

test("beginStartingBlock marks the block intro as starting", () => {
  // Given: one block-intro session is ready to begin.
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  reviewSession.preload.loaded = reviewSession.preload.total;
  const blockIntroSession = beginBlockIntro(reviewSession);

  // When: the start delay begins.
  const startingSession = beginStartingBlock(blockIntroSession);

  // Then: the block intro stays active but enters the starting phase.
  assert.equal(startingSession.state, SessionStateKind.BlockIntro);
  assert.equal(startingSession.starting, true);
  assert.equal(startingSession.currentBlockIndex, blockIntroSession.currentBlockIndex);
});

test("beginTrial carries queued uploads into the trial session", () => {
  // Given: one block-intro session is ready to begin with pending upload state.
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  reviewSession.preload.loaded = reviewSession.preload.total;
  const blockIntroSession = beginBlockIntro(reviewSession);
  blockIntroSession.blockUpload.pendingUpload = {
    blockIndex: 1,
    payload: { trials: [{ events: [] }] },
  };

  // When: the trial session is created.
  const trialSession = beginTrial(blockIntroSession);

  // Then: the state changes to trial while dropping block-intro-only upload state.
  assert.equal(trialSession.state, SessionStateKind.Trial);
  assert.equal(trialSession.currentBlockIndex, blockIntroSession.currentBlockIndex);
  assert.equal("blockUpload" in trialSession, false);
  assert.equal(trialSession.currentTrialIndex, 0);
  assert.deepEqual(trialSession.currentBlockTrials, []);
  assert.equal(trialSession.trial.startedAtMs, null);
  assert.equal(beginStartingBlock(blockIntroSession).starting, true);
});
