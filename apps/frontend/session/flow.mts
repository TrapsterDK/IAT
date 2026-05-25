import type { FrontendApiClient } from "../core/api_adapter.mjs";
import {
  PRELOAD_CONCURRENCY,
  PRELOAD_HEARTBEAT_INTERVAL_MS,
  START_BLOCK_DELAY_MS,
  TRIAL_ADVANCE_DELAY_MS,
} from "../core/config.mjs";
import { apiErrorMessage, unknownErrorMessage } from "../core/errors.mjs";
import { collectImageUrls } from "../state/selectors.mjs";
import {
  type CompletedTrial,
  ResponseSide,
  SessionStateKind,
  type SessionMode,
  type RuntimeState,
  TrialAdvanceKind,
  TrialResponseKind,
} from "../state/types.mjs";
import { sleep } from "../core/utils.mjs";
import { beginStartingBlock } from "../state/states/block_intro.mjs";
import { storeSessionResult } from "../state/states/result.mjs";
import {
  applyPreloadProgress,
  beginBlockIntro,
  setPreloadRunning,
  type PreloadProgressSnapshot,
} from "../state/states/preloading.mjs";
import { beginPreloading, createSessionState } from "../state/states/review.mjs";
import { beginTrial } from "../state/states/starting_block.mjs";
import {
  hasBlockUploads,
  hasPendingBlockUploads,
  markBlockUploadFailed,
  markBlockUploadStarted,
  markBlockUploadUploaded,
  nextPendingBlockUpload,
  setBlockUploadsActive,
} from "../state/block_uploads.mjs";
import { advanceSessionAfterCompletedTrial, registerTrialResponse } from "../state/states/trial.mjs";
import { ensureImageObjectUrl, revokeImageObjectUrls } from "./image_cache.mjs";

export function createBrowserSessionFlowEnvironment() {
  return {
    clearInterval: (timerId: number) => window.clearInterval(timerId),
    getClientContext: () => {
      const userAgentData = navigator as Navigator & {
        userAgentData?: {
          platform?: string;
        };
      };
      const platform = userAgentData.userAgentData?.platform?.trim() ?? "";
      const userAgent = navigator.userAgent.trim();

      return {
        devicePixelRatio:
          Number.isFinite(window.devicePixelRatio) && window.devicePixelRatio > 0 ? window.devicePixelRatio : null,
        platform: platform === "" ? null : platform,
        userAgent: userAgent === "" ? null : userAgent,
        viewportHeightPx: window.innerHeight > 0 ? window.innerHeight : null,
        viewportWidthPx: window.innerWidth > 0 ? window.innerWidth : null,
      };
    },
    getNow: () => new Date(),
    getPerformanceNow: () => performance.now(),
    setInterval: (callback: () => void, intervalMs: number) => window.setInterval(callback, intervalMs),
    setTimeout: (callback: () => void, delayMs: number) => window.setTimeout(callback, delayMs),
    sleep,
  };
}

export function createSessionFlow(
  runtime: RuntimeState,
  render: () => void,
  api: FrontendApiClient,
  environment: ReturnType<typeof createBrowserSessionFlowEnvironment>,
  sessionMode: SessionMode | null = null,
  planSeed: number | null = null,
) {
  let blockUploadPromise: Promise<void> | null = null;
  let preloadPromise: Promise<void> | null = null;
  let preloadHeartbeatId: number | null = null;
  function currentSessionOrNull(sessionKey: string) {
    const session = runtime.session;
    if (session === null || session.bootstrap.session_key !== sessionKey) {
      return null;
    }

    return session;
  }

  async function fetchCatalog() {
    if (runtime.catalog.loading) {
      return;
    }

    runtime.catalog.loading = true;
    runtime.catalog.error = null;
    render();

    try {
      const listIatsResult = await api.listIats();
      if (listIatsResult.data === undefined) {
        runtime.catalog.error = await apiErrorMessage(listIatsResult, "Unable to load the test catalog.");
        runtime.catalog.items = [];
        return;
      }

      runtime.catalog.items = listIatsResult.data;
    } catch (error: unknown) {
      runtime.catalog.error = unknownErrorMessage(error);
    } finally {
      runtime.catalog.loading = false;
      render();
    }
  }

  async function startSession(iatSlug: string) {
    if (runtime.session !== null || runtime.catalog.startingIatSlug !== null || preloadPromise !== null) {
      return;
    }

    runtime.catalog.startingIatSlug = iatSlug;
    runtime.ui.screenError = null;
    render();

    try {
      revokeImageObjectUrls(runtime.assets.imageObjectUrls);
      const clientContext = environment.getClientContext();

      const iatDetailResult = await api.getIat(iatSlug);
      if (iatDetailResult.data === undefined) {
        runtime.ui.screenError = await apiErrorMessage(iatDetailResult, "Unable to load the selected test.");
        return;
      }

      const createSessionResult = await api.createSession({ clientContext, iatSlug, planSeed, sessionMode });
      if (createSessionResult.data === undefined) {
        runtime.ui.screenError = await apiErrorMessage(createSessionResult, "Unable to start the session.");
        return;
      }

      runtime.session = createSessionState(iatDetailResult.data, createSessionResult.data);
      render();
    } catch (error: unknown) {
      runtime.ui.screenError = unknownErrorMessage(error);
    } finally {
      runtime.catalog.startingIatSlug = null;
      render();
    }
  }

  async function beginTest() {
    const session = runtime.session;
    if (session === null || session.state !== SessionStateKind.Review) {
      return;
    }

    runtime.session = beginPreloading(session, environment.getNow());
    render();
    await preloadSessionImages();
  }

  async function beginCurrentBlock() {
    const session = runtime.session;
    if (session === null || session.state !== SessionStateKind.BlockIntro) {
      return;
    }

    const sessionKey = session.bootstrap.session_key;

    runtime.session = beginStartingBlock(session);
    render();

    await environment.sleep(START_BLOCK_DELAY_MS);

    const trackedSession = currentSessionOrNull(sessionKey);
    if (trackedSession === null || trackedSession.state !== SessionStateKind.StartingBlock) {
      return;
    }

    runtime.session = beginTrial(trackedSession, environment.getPerformanceNow());
    render();
  }

  function registerResponse(side: ResponseSide) {
    const session = runtime.session;
    if (session === null || session.state !== SessionStateKind.Trial) {
      return;
    }

    const now = environment.getPerformanceNow();
    const elapsedMs = Math.max(0, Math.round(now - session.trial.startedAtMs));
    const responseResult = registerTrialResponse(session, side, elapsedMs);
    if (responseResult.kind === TrialResponseKind.Ignored) {
      return;
    }

    render();

    if (responseResult.kind !== TrialResponseKind.Accepted) {
      return;
    }

    const sessionKey = session.bootstrap.session_key;
    const completedTrial = responseResult.completedTrial;

    environment.setTimeout(() => {
      advanceTrial(sessionKey, completedTrial);
    }, TRIAL_ADVANCE_DELAY_MS);
  }

  function advanceTrial(sessionKey: string, completedTrial: CompletedTrial) {
    const session = currentSessionOrNull(sessionKey);
    if (session === null || session.state !== SessionStateKind.Trial) {
      return;
    }

    const advanceResult = advanceSessionAfterCompletedTrial(session, completedTrial, environment.getPerformanceNow());
    runtime.session = advanceResult.session;
    render();

    if (advanceResult.kind === TrialAdvanceKind.Ignored) {
      return;
    }

    void flushQueuedBlockUploads();
  }

  async function preloadSessionImages() {
    if (preloadPromise !== null) {
      return preloadPromise;
    }

    const session = runtime.session;
    if (session === null || session.state !== SessionStateKind.Preloading) {
      return;
    }

    const sessionKey = session.bootstrap.session_key;

    const currentPreloadPromise = (async () => {
      // Keep newly created object URLs local until this preload still belongs to the active session.
      const preloadedImageObjectUrls = new Map<string, string>();
      try {
        const imageUrls = collectImageUrls(session.bootstrap);
        const remainingUrls: string[] = [];
        let loaded = 0;

        for (const imageUrl of imageUrls) {
          if (runtime.assets.imageObjectUrls.has(imageUrl)) {
            loaded += 1;
          } else {
            remainingUrls.push(imageUrl);
          }
        }

        const startedAt = environment.getNow();
        const preloadProgress: PreloadProgressSnapshot = {
          failures: [],
          inFlightCount: 0,
          lastProgressAt: startedAt,
          loaded,
          startedAt,
          total: imageUrls.length,
        };

        function currentPreloadingSessionOrNull() {
          const currentSession = currentSessionOrNull(sessionKey);
          if (currentSession === null || currentSession.state !== SessionStateKind.Preloading) {
            return null;
          }

          return currentSession;
        }

        function renderPreloadProgress() {
          const currentSession = currentPreloadingSessionOrNull();
          if (currentSession === null) {
            return false;
          }

          applyPreloadProgress(currentSession, preloadProgress);
          render();
          return true;
        }

        const currentSession = currentPreloadingSessionOrNull();
        if (currentSession === null) {
          return;
        }

        setPreloadRunning(currentSession, true);
        applyPreloadProgress(currentSession, preloadProgress);
        render();

        if (remainingUrls.length === 0) {
          runtime.session = beginBlockIntro(currentSession);
          render();
          return;
        }

        startPreloadHeartbeat();

        const workerCount = Math.min(PRELOAD_CONCURRENCY, remainingUrls.length);
        let nextImageIndex = 0;

        async function worker() {
          while (nextImageIndex < remainingUrls.length) {
            const imageUrl = remainingUrls[nextImageIndex];
            nextImageIndex += 1;

            if (imageUrl === undefined) {
              return;
            }

            preloadProgress.inFlightCount += 1;
            if (!renderPreloadProgress()) {
              return;
            }

            try {
              const objectUrl = await ensureImageObjectUrl(imageUrl, preloadedImageObjectUrls);
              if (currentSessionOrNull(sessionKey) === null) {
                URL.revokeObjectURL(objectUrl);
                preloadedImageObjectUrls.delete(imageUrl);
                return;
              }

              runtime.assets.imageObjectUrls.set(imageUrl, objectUrl);
              preloadedImageObjectUrls.delete(imageUrl);
              preloadProgress.loaded += 1;
            } catch {
              preloadProgress.failures.push(imageUrl);
            } finally {
              preloadProgress.inFlightCount = Math.max(0, preloadProgress.inFlightCount - 1);
            }

            preloadProgress.lastProgressAt = environment.getNow();
            if (!renderPreloadProgress()) {
              return;
            }
          }
        }

        await Promise.all(Array.from({ length: workerCount }, () => worker()));

        const finishedSession = currentPreloadingSessionOrNull();
        if (finishedSession === null) {
          return;
        }

        applyPreloadProgress(finishedSession, preloadProgress);
        if (preloadProgress.failures.length === 0) {
          runtime.session = beginBlockIntro(finishedSession);
        }
        render();
      } finally {
        revokeImageObjectUrls(preloadedImageObjectUrls);
      }
    })()
      .catch((error: unknown) => {
        if (currentSessionOrNull(sessionKey) !== null) {
          runtime.ui.screenError = unknownErrorMessage(error);
        }
      })
      .finally(() => {
        const currentSession = currentSessionOrNull(sessionKey);
        if (currentSession !== null && currentSession.state === SessionStateKind.Preloading) {
          setPreloadRunning(currentSession, false);
          render();
        }

        if (preloadPromise === currentPreloadPromise) {
          preloadPromise = null;
          stopPreloadHeartbeat();
        }
      });

    preloadPromise = currentPreloadPromise;

    return preloadPromise;
  }

  async function flushQueuedBlockUploads() {
    if (blockUploadPromise !== null) {
      return blockUploadPromise;
    }

    const session = runtime.session;
    if (session === null || !hasBlockUploads(session)) {
      return;
    }

    const sessionKey = session.bootstrap.session_key;

    const currentBlockUploadPromise = (async () => {
      const currentSession = currentSessionOrNull(sessionKey);
      if (currentSession === null || !hasBlockUploads(currentSession)) {
        return;
      }

      if (currentSession.state === SessionStateKind.Finalizing) {
        currentSession.pendingScoreError = null;
      }
      setBlockUploadsActive(currentSession, true);
      render();

      while (true) {
        const currentSession = currentSessionOrNull(sessionKey);
        if (currentSession === null || !hasBlockUploads(currentSession)) {
          return;
        }

        const queuedUpload = nextPendingBlockUpload(currentSession);
        if (queuedUpload === null) {
          break;
        }

        markBlockUploadStarted(queuedUpload);
        render();

        try {
          const completeBlockResult = await api.completeBlock(
            sessionKey,
            queuedUpload.blockIndex,
            queuedUpload.payload,
          );
          if (currentSessionOrNull(sessionKey) === null) {
            return;
          }

          if (completeBlockResult.data === undefined) {
            markBlockUploadFailed(
              queuedUpload,
              await apiErrorMessage(completeBlockResult, "Unable to upload the block."),
            );
            render();
            return;
          }

          markBlockUploadUploaded(queuedUpload);
          render();
        } catch (error: unknown) {
          if (currentSessionOrNull(sessionKey) === null) {
            return;
          }

          markBlockUploadFailed(queuedUpload, unknownErrorMessage(error));
          render();
          return;
        }
      }

      const refreshedSession = currentSessionOrNull(sessionKey);
      if (refreshedSession === null) {
        return;
      }

      if (refreshedSession.state !== SessionStateKind.Finalizing || hasPendingBlockUploads(refreshedSession)) {
        return;
      }

      try {
        const scoreResult = await api.getScore(sessionKey);
        const currentSession = currentSessionOrNull(sessionKey);
        if (currentSession === null || currentSession.state !== SessionStateKind.Finalizing) {
          return;
        }

        if (scoreResult.data === undefined) {
          const pendingScoreError = await apiErrorMessage(scoreResult, "Unable to calculate the result.");
          if (scoreResult.response.status === 422) {
            runtime.session = storeSessionResult(currentSession, null, pendingScoreError);
            render();
            return;
          }

          currentSession.pendingScoreError = pendingScoreError;
          return;
        }

        runtime.session = storeSessionResult(currentSession, scoreResult.data, null);
        render();
      } catch (error: unknown) {
        const currentSession = currentSessionOrNull(sessionKey);
        if (currentSession !== null && currentSession.state === SessionStateKind.Finalizing) {
          currentSession.pendingScoreError = unknownErrorMessage(error);
        }
      }
    })().finally(() => {
      const currentSession = currentSessionOrNull(sessionKey);
      if (currentSession !== null && hasBlockUploads(currentSession)) {
        setBlockUploadsActive(currentSession, false);
        render();
      }

      if (blockUploadPromise === currentBlockUploadPromise) {
        blockUploadPromise = null;
      }
    });

    blockUploadPromise = currentBlockUploadPromise;

    return blockUploadPromise;
  }

  function clearSession() {
    const session = runtime.session;
    if (session !== null) {
      if (session.state === SessionStateKind.Preloading) {
        setPreloadRunning(session, false);
      } else if (hasBlockUploads(session)) {
        setBlockUploadsActive(session, false);
      }
    }

    runtime.session = null;
    runtime.ui.screenError = null;
    preloadPromise = null;
    blockUploadPromise = null;
    stopPreloadHeartbeat();
    revokeImageObjectUrls(runtime.assets.imageObjectUrls);
    render();
  }

  function startPreloadHeartbeat() {
    if (preloadHeartbeatId !== null) {
      return;
    }

    preloadHeartbeatId = environment.setInterval(() => {
      if (runtime.session?.state !== SessionStateKind.Preloading || runtime.session.preload.running !== true) {
        stopPreloadHeartbeat();
        return;
      }

      render();
    }, PRELOAD_HEARTBEAT_INTERVAL_MS);
  }

  function stopPreloadHeartbeat() {
    if (preloadHeartbeatId === null) {
      return;
    }

    environment.clearInterval(preloadHeartbeatId);
    preloadHeartbeatId = null;
  }

  return {
    beginTest,
    beginCurrentBlock,
    clearSession,
    fetchCatalog,
    flushQueuedBlockUploads,
    preloadSessionImages,
    registerResponse,
    startSession,
  };
}
