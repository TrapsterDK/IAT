import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../../testing/fixtures.mjs";
import { beginStartingBlock } from "./block_intro.mjs";
import { beginBlockIntro } from "./preloading.mjs";
import { storeSessionResult } from "./result.mjs";
import { beginPreloading, createSessionState } from "./review.mjs";
import { beginTrial } from "./starting_block.mjs";
import { SessionStateKind, type FinalizingSessionState } from "../types.mjs";

test("storeSessionResult removes upload state and stores the final score payload", () => {
  // Given: one finalizing session holds pending upload metadata before scoring completes
  const trialSession = beginTrial(
    beginStartingBlock(
      beginBlockIntro(beginPreloading(createSessionState(createIatDetailFixture(), createBootstrapFixture()))),
    ),
    15,
  );
  const { trial, ...sessionWithoutTrial } = trialSession;
  void trial;
  const finalizingSession: FinalizingSessionState = {
    ...sessionWithoutTrial,
    pendingScoreError: "Stale score error.",
    state: SessionStateKind.Finalizing,
  };

  // When: the final score is stored on the session
  const resultSession = storeSessionResult(finalizingSession, { d_score: 0.42, headline: "Result ready." }, null);

  // Then: the result session keeps the score data for the completed session
  assert.equal(resultSession.state, SessionStateKind.Results);
  assert.deepEqual(resultSession.result, {
    score: { d_score: 0.42, headline: "Result ready." },
    scoreError: null,
  });
});
