import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../../testing/fixtures.mjs";
import { applyPreloadProgress, beginBlockIntro, setPreloadRunning } from "./preloading.mjs";
import { beginPreloading, createSessionState } from "./review.mjs";
import { SessionStateKind } from "../types.mjs";

test("applyPreloadProgress copies the preload progress snapshot into session state", () => {
  // Given: one preloading session and one snapshot of preload progress
  const session = beginPreloading(createSessionState(createIatDetailFixture(), createBootstrapFixture()));
  const startedAt = new Date("2026-01-02T03:04:05.000Z");
  const lastProgressAt = new Date("2026-01-02T03:04:07.000Z");
  const preloadProgress = {
    failures: ["https://example.test/missing.png"],
    inFlightCount: 2,
    lastProgressAt,
    loaded: 3,
    startedAt,
    total: 5,
  };

  // When: the preload snapshot is applied to the session
  applyPreloadProgress(session, preloadProgress);
  preloadProgress.failures.push("https://example.test/later.png");

  // Then: the session keeps copied progress fields and an isolated failures array
  assert.equal(session.preload.total, 5);
  assert.equal(session.preload.loaded, 3);
  assert.equal(session.preload.inFlightCount, 2);
  assert.deepEqual(session.preload.failures, ["https://example.test/missing.png"]);
  assert.equal(session.preload.startedAt, startedAt);
  assert.equal(session.preload.lastProgressAt, lastProgressAt);
});

test("setPreloadRunning updates the preload running flag", () => {
  // Given: one preloading session starts idle before loading begins
  const session = beginPreloading(createSessionState(createIatDetailFixture(), createBootstrapFixture()));

  // When: the preload state is marked running and then idle again
  setPreloadRunning(session, true);

  // Then: the running flag is enabled for active preloading work
  assert.equal(session.preload.running, true);

  // When: the preload work stops running
  setPreloadRunning(session, false);

  // Then: the running flag is disabled again
  assert.equal(session.preload.running, false);
});

test("beginBlockIntro drops preload metadata and starts at the first block", () => {
  // Given: one preloading session has already collected preload state
  const session = beginPreloading(createSessionState(createIatDetailFixture(), createBootstrapFixture()));

  // When: the session transitions into the block-intro stage
  const blockIntroSession = beginBlockIntro(session);

  // Then: the first block becomes active
  assert.equal(blockIntroSession.state, SessionStateKind.BlockIntro);
  assert.equal(blockIntroSession.currentBlockIndex, 0);
});
