import type {
  ResponseSide as BackendResponseSide,
  CompletedBlockRequest,
  CreateSessionRequest,
} from "@iat/apps/api/backend";

import { ResponseSide } from "../state/types.mjs";
import { createApiClient, type ApiClient } from "./api.mjs";

import type { ClientContext, CompletedBlockPayload, IatDetail, SessionBootstrap } from "../state/types.mjs";

type FrontendApiResult<T> =
  | {
      data: T;
      error?: never;
      response: Response;
    }
  | {
      data?: never;
      error: unknown;
      response: Response;
    };

export interface CreateSessionInput {
  clientContext: ClientContext;
  iatSlug: string;
}

export function createFrontendApiClient(timeoutMs: number, baseUrl = ""): FrontendApiClient {
  return createFrontendApiAdapter(createApiClient(timeoutMs, baseUrl));
}

export function createFrontendApiAdapter(api: ApiClient) {
  return {
    async listIats() {
      return mapApiResult(await api.listIats(), (payload) => payload);
    },

    async getIat(slug: string) {
      return mapApiResult(await api.getIat(slug), mapIatDetail);
    },

    async createSession(request: CreateSessionInput) {
      return mapApiResult(await api.createSession(mapCreateSessionRequest(request)), mapSessionBootstrap);
    },

    async completeBlock(sessionKey: string, blockIndex: number, request: CompletedBlockPayload) {
      return mapApiResult(
        await api.completeBlock(sessionKey, blockIndex, mapCompletedBlockRequest(request)),
        () => null,
      );
    },

    async getScore(sessionKey: string) {
      return mapApiResult(await api.getScore(sessionKey), (payload) => payload);
    },
  };
}
export type FrontendApiClient = ReturnType<typeof createFrontendApiAdapter>;

function mapApiResult<T, U>(result: FrontendApiResult<T>, map: (data: T) => U): FrontendApiResult<U> {
  if ("error" in result) {
    return { error: result.error, response: result.response };
  }

  return { data: map(result.data), response: result.response };
}

function mapIatDetail(payload: NonNullable<Awaited<ReturnType<ApiClient["getIat"]>>["data"]>): IatDetail {
  return {
    categories: payload.categories.map((group) => ({
      category: group.category.map((category) => ({
        label: category.label,
        slug: category.slug,
        stimuli: category.stimuli.map(mapStimulus),
      })),
    })),
    description: payload.description,
    slug: payload.slug,
    title: payload.title,
  };
}

function mapSessionBootstrap(
  payload: NonNullable<Awaited<ReturnType<ApiClient["createSession"]>>["data"]>,
): SessionBootstrap {
  return {
    blocks: payload.blocks.map((block) => ({
      is_practice: block.is_practice,
      left_labels: [...block.left_labels],
      right_labels: [...block.right_labels],
      trials: block.trials.map((trial) => ({
        correct_response_side: mapResponseSide(trial.correct_response_side),
        stimulus: mapStimulus(trial.stimulus),
      })),
    })),
    session_key: payload.session_key,
  };
}

function mapCreateSessionRequest(request: CreateSessionInput): CreateSessionRequest {
  const { clientContext } = request;
  const mappedClientContext: NonNullable<CreateSessionRequest["client_context"]> = {};

  if (clientContext.devicePixelRatio !== null) {
    mappedClientContext.device_pixel_ratio = clientContext.devicePixelRatio;
  }

  if (clientContext.platform !== null) {
    mappedClientContext.platform = clientContext.platform;
  }

  if (clientContext.userAgent !== null) {
    mappedClientContext.user_agent = clientContext.userAgent;
  }

  if (clientContext.viewportHeightPx !== null) {
    mappedClientContext.viewport_height_px = clientContext.viewportHeightPx;
  }

  if (clientContext.viewportWidthPx !== null) {
    mappedClientContext.viewport_width_px = clientContext.viewportWidthPx;
  }

  return {
    client_context: mappedClientContext,
    iat_slug: request.iatSlug,
  };
}

function mapCompletedBlockRequest(request: CompletedBlockPayload): CompletedBlockRequest {
  return {
    trials: request.trials.map((trial) => ({
      events: trial.events.map((event) => ({
        elapsed_ms: event.elapsedMs,
        event_type: mapTrialEventType(event.eventType),
      })),
    })),
  };
}

function mapResponseSide(side: BackendResponseSide): ResponseSide {
  return side === "left" ? ResponseSide.Left : ResponseSide.Right;
}

function mapTrialEventType(side: ResponseSide): "left" | "right" {
  return side === ResponseSide.Left ? "left" : "right";
}

function mapStimulus(payload: { image_url?: string | null; text?: string | null }) {
  return {
    image_url: payload.image_url ?? null,
    text: payload.text ?? null,
  };
}
