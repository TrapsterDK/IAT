import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../../testing/fixtures.mjs";
import { applyPreloadProgress, beginBlockIntro, createSessionState, setPreloadRunning } from "./review.mjs";
import { SessionStateKind } from "../types.mjs";

test("createSessionState stores the IAT detail, bootstrap, and seeded preload state", () => {
  // Given: one IAT detail payload, one session bootstrap payload, and one seeded start time.
  const iatDetail = createIatDetailFixture();
  const bootstrap = createBootstrapFixture();
  const startedAt = new Date("2026-02-03T04:05:06.000Z");

  // When: the initial review session is created.
  const reviewSession = createSessionState(iatDetail, bootstrap, startedAt);

  // Then: the review session keeps the original payloads and seeded preload state.
  assert.equal(reviewSession.state, SessionStateKind.Review);
  assert.equal(reviewSession.iatDetail, iatDetail);
  assert.equal(reviewSession.bootstrap, bootstrap);
  assert.deepEqual(reviewSession.preload.failures, []);
  assert.equal(reviewSession.preload.inFlightCount, 0);
  assert.equal(reviewSession.preload.loaded, 0);
  assert.equal(reviewSession.preload.running, false);
  assert.equal(reviewSession.preload.startedAt, startedAt);
  assert.equal(reviewSession.preload.lastProgressAt, startedAt);
  assert.equal(reviewSession.preload.total, 0);
});

test("createSessionState counts distinct image URLs in seeded preload state", () => {
  // Given: one bootstrap contains repeated and null image URLs.
  const bootstrap = createBootstrapFixture();
  const baseBlock = bootstrap.blocks[0];
  const baseTrial = baseBlock?.trials[0];
  if (baseBlock === undefined || baseTrial === undefined) {
    throw new Error("Expected one base block and trial fixture.");
  }

  // When: the review session is created.
  const reviewSession = createSessionState(createIatDetailFixture(), {
    ...bootstrap,
    blocks: [
      {
        ...baseBlock,
        trials: [
          { ...baseTrial, stimulus: { image_url: "https://example.test/alpha.png", text: null } },
          { ...baseTrial, stimulus: { image_url: "https://example.test/alpha.png", text: null } },
          { ...baseTrial, stimulus: { image_url: "https://example.test/beta.png", text: null } },
          { ...baseTrial, stimulus: { image_url: null, text: "alpha" } },
        ],
      },
    ],
  });

  // Then: the preload state is seeded with the distinct image count.
  assert.equal(reviewSession.preload.total, 2);
});

test("applyPreloadProgress copies the preload progress snapshot into review state", () => {
  // Given: one review session and one snapshot of preload progress.
  const session = createSessionState(createIatDetailFixture(), createBootstrapFixture());
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

  // When: the preload snapshot is applied to the session.
  applyPreloadProgress(session, preloadProgress);
  preloadProgress.failures.push("https://example.test/later.png");

  // Then: the session keeps copied progress fields and an isolated failures array.
  assert.equal(session.preload.total, 5);
  assert.equal(session.preload.loaded, 3);
  assert.equal(session.preload.inFlightCount, 2);
  assert.deepEqual(session.preload.failures, ["https://example.test/missing.png"]);
  assert.equal(session.preload.startedAt, startedAt);
  assert.equal(session.preload.lastProgressAt, lastProgressAt);
});

test("setPreloadRunning updates the preload running flag", () => {
  // Given: one review session starts idle before loading begins.
  const session = createSessionState(createIatDetailFixture(), createBootstrapFixture());

  // When: the preload state is marked running and then idle again.
  setPreloadRunning(session, true);

  // Then: the running flag is enabled for active preloading work.
  assert.equal(session.preload.running, true);

  // When: the preload work stops running.
  setPreloadRunning(session, false);

  // Then: the running flag is disabled again.
  assert.equal(session.preload.running, false);
});

test("beginBlockIntro drops preload metadata and starts at the first block", () => {
  // Given: one review session has already collected preload state.
  const session = createSessionState(createIatDetailFixture(), createBootstrapFixture());

  // When: the session transitions into the block-intro stage.
  const blockIntroSession = beginBlockIntro(session);

  // Then: the first block becomes active with empty upload state.
  assert.equal(blockIntroSession.state, SessionStateKind.BlockIntro);
  assert.equal(blockIntroSession.currentBlockIndex, 0);
  assert.equal(blockIntroSession.blockUpload.pendingUpload, null);
  assert.equal(blockIntroSession.blockUpload.uploadError, null);
  assert.equal(blockIntroSession.blockUpload.uploading, false);
});
