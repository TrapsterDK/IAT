import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../../testing/fixtures.mjs";
import { beginPreloading, createSessionState } from "./review.mjs";
import { SessionStateKind } from "../types.mjs";

test("createSessionState stores the IAT detail and bootstrap in review state", () => {
  // Given: one IAT detail payload and one session bootstrap payload
  const iatDetail = createIatDetailFixture();
  const bootstrap = createBootstrapFixture();

  // When: the initial review session is created
  const reviewSession = createSessionState(iatDetail, bootstrap);

  // Then: the review session keeps the original bootstrap and detail payloads
  assert.equal(reviewSession.state, SessionStateKind.Review);
  assert.equal(reviewSession.iatDetail, iatDetail);
  assert.equal(reviewSession.bootstrap, bootstrap);
});

test("beginPreloading counts distinct image URLs and seeds idle preload state", () => {
  // Given: one review session contains repeated and null image URLs
  const bootstrap = createBootstrapFixture();
  const baseBlock = bootstrap.blocks[0];
  const baseTrial = baseBlock?.trials[0];
  if (baseBlock === undefined || baseTrial === undefined) {
    throw new Error("Expected one base block and trial fixture.");
  }
  const startedAt = new Date("2026-02-03T04:05:06.000Z");
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

  // When: the review session begins preloading
  const preloadingSession = beginPreloading(reviewSession, startedAt);

  // Then: the preload state starts idle with the distinct image count and timestamps seeded
  assert.equal(preloadingSession.state, SessionStateKind.Preloading);
  assert.deepEqual(preloadingSession.preload.failures, []);
  assert.equal(preloadingSession.preload.inFlightCount, 0);
  assert.equal(preloadingSession.preload.loaded, 0);
  assert.equal(preloadingSession.preload.running, false);
  assert.equal(preloadingSession.preload.startedAt, startedAt);
  assert.equal(preloadingSession.preload.lastProgressAt, startedAt);
  assert.equal(preloadingSession.preload.total, 2);
});
