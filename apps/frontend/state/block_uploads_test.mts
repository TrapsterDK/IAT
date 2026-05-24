import assert from "node:assert/strict";
import { test } from "node:test";

import { createBootstrapFixture, createIatDetailFixture } from "../testing/fixtures.mjs";
import { beginStartingBlock } from "./states/block_intro.mjs";
import { beginBlockIntro } from "./states/preloading.mjs";
import { beginPreloading, createSessionState } from "./states/review.mjs";
import { beginTrial } from "./states/starting_block.mjs";
import {
  hasBlockUploads,
  hasPendingBlockUploads,
  markBlockUploadFailed,
  markBlockUploadStarted,
  markBlockUploadUploaded,
  nextPendingBlockUpload,
  setBlockUploadsActive,
} from "./block_uploads.mjs";
import { ResponseSide, SessionStateKind, type FinalizingSessionState, type QueuedBlockUpload } from "./types.mjs";

test("hasBlockUploads returns true only for upload-owning session states", () => {
  // Given: review, block-intro, starting-block, trial, and finalizing sessions share one bootstrap
  const reviewSession = createSessionState(createIatDetailFixture(), createBootstrapFixture());
  const blockIntroSession = beginBlockIntro(beginPreloading(reviewSession));
  const startingBlockSession = beginStartingBlock(blockIntroSession);
  const trialSession = beginTrial(startingBlockSession, 25);
  const { trial, ...sessionWithoutTrial } = trialSession;
  void trial;
  const finalizingSession: FinalizingSessionState = {
    ...sessionWithoutTrial,
    pendingScoreError: null,
    state: SessionStateKind.Finalizing,
  };

  // When: each session is checked for block-upload support
  const reviewHasUploads = hasBlockUploads(reviewSession);
  const blockIntroHasUploads = hasBlockUploads(blockIntroSession);
  const startingBlockHasUploads = hasBlockUploads(startingBlockSession);
  const trialHasUploads = hasBlockUploads(trialSession);
  const finalizingHasUploads = hasBlockUploads(finalizingSession);

  // Then: only the upload-owning states report queued upload support
  assert.equal(reviewHasUploads, false);
  assert.equal(blockIntroHasUploads, true);
  assert.equal(startingBlockHasUploads, true);
  assert.equal(trialHasUploads, true);
  assert.equal(finalizingHasUploads, true);
});

test("nextPendingBlockUpload returns the first queued upload that is still pending", () => {
  // Given: one starting-block session has uploaded and pending entries in its queue
  const uploadedEntry = createQueuedBlockUpload({ uploaded: true });
  const pendingEntry = createQueuedBlockUpload({ blockIndex: 2, uploaded: false });
  const session = createStartingBlockSession([uploadedEntry, pendingEntry]);

  // When: the next pending upload is requested
  const nextUpload = nextPendingBlockUpload(session);

  // Then: the first still-pending queue entry is returned
  assert.equal(nextUpload, pendingEntry);
});

test("nextPendingBlockUpload returns null when no queued upload is still pending", () => {
  // Given: one starting-block session has only already-uploaded queue entries
  const session = createStartingBlockSession([createQueuedBlockUpload({ uploaded: true })]);

  // When: the next pending upload is requested
  const nextUpload = nextPendingBlockUpload(session);

  // Then: the queue reports that no pending upload remains
  assert.equal(nextUpload, null);
});

test("hasPendingBlockUploads returns true when any queued upload is still pending", () => {
  // Given: one starting-block session still has one queued upload marked pending
  const session = createStartingBlockSession([createQueuedBlockUpload({ uploaded: false })]);

  // When: pending upload state is checked
  const hasPendingUploads = hasPendingBlockUploads(session);

  // Then: the session reports that block uploads are still pending
  assert.equal(hasPendingUploads, true);
});

test("hasPendingBlockUploads returns false when every queued upload has finished", () => {
  // Given: one starting-block session has only uploaded queue entries left
  const session = createStartingBlockSession([createQueuedBlockUpload({ uploaded: true })]);

  // When: pending upload state is checked
  const hasPendingUploads = hasPendingBlockUploads(session);

  // Then: the session reports that no block uploads remain pending
  assert.equal(hasPendingUploads, false);
});

test("setBlockUploadsActive updates the session uploading flag", () => {
  // Given: one starting-block session is idle before upload work begins
  const session = createStartingBlockSession([createQueuedBlockUpload()]);

  // When: block uploads are marked active
  setBlockUploadsActive(session, true);

  // Then: the uploading flag reflects the active upload state
  assert.equal(session.blockUploads.uploading, true);

  // When: block uploads are marked inactive again
  setBlockUploadsActive(session, false);

  // Then: the uploading flag returns to the idle state
  assert.equal(session.blockUploads.uploading, false);
});

test("markBlockUploadStarted clears the last error before another upload attempt", () => {
  // Given: one queued upload already recorded one previous failure
  const queuedUpload = createQueuedBlockUpload({ lastError: "Previous failure." });

  // When: the queued upload starts another attempt
  markBlockUploadStarted(queuedUpload);

  // Then: the stale error is cleared
  assert.equal(queuedUpload.lastError, null);
});

test("markBlockUploadFailed stores the latest upload error message", () => {
  // Given: one queued upload has not yet recorded an error for the current attempt
  const queuedUpload = createQueuedBlockUpload();

  // When: the upload attempt fails
  markBlockUploadFailed(queuedUpload, "Upload failed.");

  // Then: the queued upload stores the latest failure message
  assert.equal(queuedUpload.lastError, "Upload failed.");
});

test("markBlockUploadUploaded marks the upload complete and clears any error", () => {
  // Given: one queued upload finishes after previously recording an upload error
  const queuedUpload = createQueuedBlockUpload({ lastError: "Upload failed." });

  // When: the upload completes successfully
  markBlockUploadUploaded(queuedUpload);

  // Then: the upload records completion and clears the error
  assert.equal(queuedUpload.lastError, null);
  assert.equal(queuedUpload.uploaded, true);
});

function createStartingBlockSession(queuedBlockUploads: QueuedBlockUpload[]) {
  const blockIntroSession = beginBlockIntro(
    beginPreloading(createSessionState(createIatDetailFixture(), createBootstrapFixture())),
  );
  blockIntroSession.blockUploads.queuedBlockUploads = queuedBlockUploads;
  return beginStartingBlock(blockIntroSession);
}

function createQueuedBlockUpload(overrides: Partial<QueuedBlockUpload> = {}): QueuedBlockUpload {
  return {
    blockIndex: 1,
    lastError: null,
    payload: { trials: [{ events: [{ elapsedMs: 30, eventType: ResponseSide.Left }] }] },
    uploaded: false,
    ...overrides,
  };
}
