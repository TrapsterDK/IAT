import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../../testing/fixtures.mjs";
import { beginStartingBlock } from "./block_intro.mjs";
import { beginBlockIntro } from "./preloading.mjs";
import { beginPreloading, createSessionState } from "./review.mjs";
import { SessionStateKind } from "../types.mjs";

test("beginStartingBlock carries queued uploads into the starting-block session", () => {
  // Given: one block-intro session is ready to begin with pending upload state
  const blockIntroSession = beginBlockIntro(
    beginPreloading(createSessionState(createIatDetailFixture(), createBootstrapFixture())),
  );

  // When: the starting-block session is created
  const startingBlockSession = beginStartingBlock(blockIntroSession);

  // Then: the state changes to starting-block while preserving the upload queue reference
  assert.equal(startingBlockSession.state, SessionStateKind.StartingBlock);
  assert.equal(startingBlockSession.currentBlockIndex, blockIntroSession.currentBlockIndex);
  assert.equal(startingBlockSession.blockUploads, blockIntroSession.blockUploads);
});
