import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../testing/fixtures.mjs";
import {
  canAdvanceSession,
  hasBlockUploads,
  hasPendingBlockUploads,
  markBlockUploadFailed,
  markBlockUploadStarted,
  markBlockUploadUploaded,
  nextPendingBlockUpload,
  setBlockUploadsActive,
} from "./block_uploads.mjs";
import { beginBlockIntro, createSessionState } from "./states/review.mjs";
import { ResponseSide, SessionStateKind, type PendingBlockUpload, type PendingResultSessionState } from "./types.mjs";

test("hasBlockUploads returns true only for upload-owning session states", () => {
  // Given: review, block-intro, trial, and pending-results sessions share one bootstrap.
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  const blockIntroSession = beginBlockIntro(reviewSession);
  const pendingResultSession: PendingResultSessionState = {
    bootstrap: createBootstrapFixture(),
    iatDetail: createIatDetailFixture(),
    blockUpload: {
      pendingUpload: createPendingBlockUpload(),
      uploadError: null,
      uploading: false,
    },
    pending: true,
    result: {
      score: null,
      scoreError: null,
    },
    state: SessionStateKind.Results,
  };

  // When: each session is checked for block-upload support.
  const reviewHasUploads = hasBlockUploads(reviewSession);
  const blockIntroHasUploads = hasBlockUploads(blockIntroSession);
  const trialHasUploads = hasBlockUploads({
    ...blockIntroSession,
    currentBlockTrials: [],
    currentTrialIndex: 0,
    state: SessionStateKind.Trial,
    trial: {
      activeEvents: [],
      responseLocked: false,
      startedAtMs: null,
    },
  });
  const pendingResultHasUploads = hasBlockUploads(pendingResultSession);

  // Then: only block-intro and pending-results sessions report upload ownership.
  assert.equal(reviewHasUploads, false);
  assert.equal(blockIntroHasUploads, true);
  assert.equal(trialHasUploads, false);
  assert.equal(pendingResultHasUploads, true);
});

test("nextPendingBlockUpload returns the pending upload", () => {
  // Given: one block-intro session has one pending upload.
  const pendingUpload = createPendingBlockUpload();
  const session = createBlockIntroSession(pendingUpload);

  // When: the next pending upload is requested.
  const nextUpload = nextPendingBlockUpload(session);

  // Then: the pending upload is returned.
  assert.equal(nextUpload, pendingUpload);
});

test("nextPendingBlockUpload returns null when no upload is pending", () => {
  // Given: one block-intro session has no pending upload entry.
  const session = createBlockIntroSession(null);

  // When: the next pending upload is requested.
  const nextUpload = nextPendingBlockUpload(session);

  // Then: no pending upload is reported.
  assert.equal(nextUpload, null);
});

test("hasPendingBlockUploads returns true when one upload is pending", () => {
  // Given: one block-intro session still has one pending upload.
  const session = createBlockIntroSession(createPendingBlockUpload());

  // When: pending upload state is checked.
  const hasPendingUploads = hasPendingBlockUploads(session);

  // Then: the session reports pending upload work.
  assert.equal(hasPendingUploads, true);
});

test("hasPendingBlockUploads returns false when no upload is pending", () => {
  // Given: one block-intro session has no pending upload work.
  const session = createBlockIntroSession(null);

  // When: pending upload state is checked.
  const hasPendingUploads = hasPendingBlockUploads(session);

  // Then: the session reports that no upload remains.
  assert.equal(hasPendingUploads, false);
});

test("canAdvanceSession returns true when review preloading is complete", () => {
  // Given: one review session has fully loaded every preload asset.
  const session = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  session.preload.loaded = session.preload.total;

  // When: review readiness is checked.
  const canAdvance = canAdvanceSession(session);

  // Then: the review can advance into the first block.
  assert.equal(canAdvance, true);
});

test("canAdvanceSession returns false when review preloading is still active", () => {
  // Given: one review session is still preloading assets.
  const session = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  session.preload.running = true;

  // When: review readiness is checked.
  const canAdvance = canAdvanceSession(session);

  // Then: the review cannot advance yet.
  assert.equal(canAdvance, false);
});

test("canAdvanceSession returns true when no block uploads are pending or active", () => {
  // Given: one block-intro session has no pending upload work.
  const session = createBlockIntroSession(null);

  // When: block readiness is checked.
  const canAdvance = canAdvanceSession(session);

  // Then: the block can begin immediately.
  assert.equal(canAdvance, true);
});

test("canAdvanceSession returns false while a previous block upload is pending", () => {
  // Given: one block-intro session is waiting for a previous block upload.
  const session = createBlockIntroSession(createPendingBlockUpload());

  // When: block readiness is checked.
  const canAdvance = canAdvanceSession(session);

  // Then: the next block cannot begin yet.
  assert.equal(canAdvance, false);
});

test("canAdvanceSession returns false while upload work is still active", () => {
  // Given: one block-intro session has no pending uploads but the upload loop is still active.
  const session = createBlockIntroSession(null);
  session.blockUpload.uploading = true;

  // When: block readiness is checked.
  const canAdvance = canAdvanceSession(session);

  // Then: the next block waits until upload work becomes idle.
  assert.equal(canAdvance, false);
});

test("canAdvanceSession returns false while the next block is in its starting delay", () => {
  // Given: one block-intro session has begun its visible start delay.
  const session = createBlockIntroSession(null);
  session.starting = true;

  // When: block readiness is checked.
  const canAdvance = canAdvanceSession(session);

  // Then: the block does not begin again while the delay is active.
  assert.equal(canAdvance, false);
});

test("setBlockUploadsActive updates the session uploading flag", () => {
  // Given: one pending-results session is idle before upload work begins.
  const session: PendingResultSessionState = {
    bootstrap: createBootstrapFixture(),
    iatDetail: createIatDetailFixture(),
    blockUpload: {
      pendingUpload: createPendingBlockUpload(),
      uploadError: null,
      uploading: false,
    },
    pending: true,
    result: {
      score: null,
      scoreError: null,
    },
    state: SessionStateKind.Results,
  };

  // When: block uploads are marked active.
  setBlockUploadsActive(session, true);

  // Then: the uploading flag reflects the active upload state.
  assert.equal(session.blockUpload.uploading, true);

  // When: block uploads are marked inactive again.
  setBlockUploadsActive(session, false);

  // Then: the uploading flag returns to the idle state.
  assert.equal(session.blockUpload.uploading, false);
});

test("markBlockUploadStarted clears the last upload error before another attempt", () => {
  // Given: one block-intro session already recorded one previous upload failure.
  const session = createBlockIntroSession(createPendingBlockUpload());
  session.blockUpload.uploadError = "Previous failure.";

  // When: the pending upload starts another attempt.
  markBlockUploadStarted(session);

  // Then: the stale upload error is cleared.
  assert.equal(session.blockUpload.uploadError, null);
});

test("markBlockUploadFailed stores the latest upload error message", () => {
  // Given: one block-intro session has not yet recorded an upload error.
  const session = createBlockIntroSession(createPendingBlockUpload());

  // When: the upload attempt fails.
  markBlockUploadFailed(session, "Upload failed.");

  // Then: the session stores the latest failure message.
  assert.equal(session.blockUpload.uploadError, "Upload failed.");
});

test("markBlockUploadUploaded clears the completed pending upload", () => {
  // Given: one block-intro session holds one pending upload.
  const session = createBlockIntroSession(createPendingBlockUpload());

  // When: the upload completes successfully.
  markBlockUploadUploaded(session);

  // Then: the pending upload and upload error are cleared.
  assert.equal(session.blockUpload.pendingUpload, null);
  assert.equal(session.blockUpload.uploadError, null);
});

function createBlockIntroSession(pendingUpload: PendingBlockUpload | null) {
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  reviewSession.preload.loaded = reviewSession.preload.total;

  const blockIntroSession = beginBlockIntro(reviewSession);
  blockIntroSession.blockUpload.pendingUpload = pendingUpload;
  return blockIntroSession;
}

function createPendingBlockUpload(overrides: Partial<PendingBlockUpload> = {}): PendingBlockUpload {
  return {
    blockIndex: 1,
    payload: { trials: [{ events: [{ elapsedMs: 30.125, eventType: ResponseSide.Left }] }] },
    ...overrides,
  };
}
