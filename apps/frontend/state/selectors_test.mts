import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../testing/fixtures.mjs";
import { collectImageUrls, currentBlock, currentTrial } from "./selectors.mjs";
import { createSessionState } from "./states/review.mjs";

test("currentBlock returns the active block for an in-range index", () => {
  // Given: one block progress state points to the first block in one bootstrap
  const bootstrap = createBootstrapFixture();
  const reviewSession = createSessionState(createIatDetailFixture(), bootstrap);
  const blockSession = {
    ...reviewSession,
    currentBlockIndex: 0,
  };

  // When: the current block is selected
  const block = currentBlock(blockSession);

  // Then: the selector returns the active block from the bootstrap payload
  assert.equal(block, bootstrap.blocks[0] ?? null);
});

test("currentBlock returns null for an out-of-range block index", () => {
  // Given: one block progress state points beyond the available blocks
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  const blockSession = {
    ...reviewSession,
    currentBlockIndex: 1,
  };

  // When: the current block is selected
  const block = currentBlock(blockSession);

  // Then: the selector reports that no active block exists
  assert.equal(block, null);
});

test("currentTrial returns the active trial for an in-range index", () => {
  // Given: one trial progress state points to the first trial of the first block
  const bootstrap = createBootstrapFixture();
  const reviewSession = createSessionState(createIatDetailFixture(), bootstrap);
  const trialSession = {
    ...reviewSession,
    currentBlockIndex: 0,
    currentBlockTrials: [],
    currentTrialIndex: 0,
  };

  // When: the current trial is selected
  const trial = currentTrial(trialSession);

  // Then: the selector returns the active trial from the bootstrap payload
  assert.equal(trial, bootstrap.blocks[0]?.trials[0] ?? null);
});

test("currentTrial returns null for an out-of-range trial index", () => {
  // Given: one trial progress state points beyond the available trials in the current block
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  const trialSession = {
    ...reviewSession,
    currentBlockIndex: 0,
    currentBlockTrials: [],
    currentTrialIndex: 1,
  };

  // When: the current trial is selected
  const trial = currentTrial(trialSession);

  // Then: the selector reports that no active trial exists
  assert.equal(trial, null);
});

test("collectImageUrls skips nulls and deduplicates repeated image URLs", () => {
  // Given: one bootstrap repeats image URLs across multiple trials and blocks
  const bootstrap = createBootstrapFixture();
  const baseBlock = bootstrap.blocks[0];
  const baseTrial = baseBlock?.trials[0];
  if (baseBlock === undefined || baseTrial === undefined) {
    throw new Error("Expected one base block and trial fixture.");
  }
  const firstImageUrl = "https://example.test/alpha.png";
  const secondImageUrl = "https://example.test/beta.png";
  const bootstrapWithImages = {
    ...bootstrap,
    blocks: [
      {
        ...baseBlock,
        trials: [
          { ...baseTrial, stimulus: { image_url: firstImageUrl, text: null } },
          { ...baseTrial, stimulus: { image_url: firstImageUrl, text: null } },
          { ...baseTrial, stimulus: { image_url: null, text: "alpha" } },
        ],
      },
      {
        ...baseBlock,
        trials: [{ ...baseTrial, stimulus: { image_url: secondImageUrl, text: null } }],
      },
    ],
  };

  // When: image URLs are collected for preloading
  const imageUrls = collectImageUrls(bootstrapWithImages);

  // Then: only distinct non-null image URLs are returned in encounter order
  assert.deepEqual(imageUrls, [firstImageUrl, secondImageUrl]);
});
