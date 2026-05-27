import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../../testing/fixtures.mjs";
import { storeSessionResult } from "./result.mjs";
import { SessionStateKind, type PendingResultSessionState } from "../types.mjs";

test("storeSessionResult removes upload state and stores the final score payload", () => {
  // Given: one pending-results session still owns one unfinished upload state.
  const pendingResultSession: PendingResultSessionState = {
    bootstrap: createBootstrapFixture(),
    iatDetail: createIatDetailFixture(),
    blockUpload: {
      pendingUpload: {
        blockIndex: 1,
        payload: { trials: [] },
      },
      uploadError: "Upload failed.",
      uploading: false,
    },
    pending: true,
    result: {
      score: null,
      scoreError: "Stale score error.",
    },
    state: SessionStateKind.Results,
  };

  // When: the final score is stored on the session.
  const resultSession = storeSessionResult(pendingResultSession, { d_score: 0.42, headline: "Result ready." }, null);

  // Then: the result session keeps the score data for the completed session.
  assert.equal(resultSession.state, SessionStateKind.Results);
  assert.equal(resultSession.pending, false);
  assert.deepEqual(resultSession.result, {
    score: { d_score: 0.42, headline: "Result ready." },
    scoreError: null,
  });
});
