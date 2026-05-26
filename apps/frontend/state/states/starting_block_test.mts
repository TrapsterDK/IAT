import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../../testing/fixtures.mjs";
import { beginStartingBlock } from "./block_intro.mjs";
import { beginBlockIntro } from "./preloading.mjs";
import { beginPreloading, createSessionState } from "./review.mjs";
import { beginTrial } from "./starting_block.mjs";
import { SessionStateKind } from "../types.mjs";

test("beginTrial starts the first trial with cleared response state", () => {
  // Given: one starting-block session is ready to begin with queued upload context
  const startingBlockSession = beginStartingBlock(
    beginBlockIntro(beginPreloading(createSessionState(createIatDetailFixture(), createBootstrapFixture()))),
  );

  // When: the trial stage begins
  const trialSession = beginTrial(startingBlockSession);

  // Then: the first trial starts unlocked with empty response history and preserved upload state
  assert.equal(trialSession.state, SessionStateKind.Trial);
  assert.equal(trialSession.currentTrialIndex, 0);
  assert.deepEqual(trialSession.currentBlockTrials, []);
  assert.deepEqual(trialSession.trial.activeEvents, []);
  assert.equal(trialSession.trial.responseLocked, false);
  assert.equal(trialSession.trial.startedAtMs, null);
  assert.equal(trialSession.blockUploads, startingBlockSession.blockUploads);
});
