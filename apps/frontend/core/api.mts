import type { CompletedBlockRequest, CreateSessionRequest, paths } from "@iat/apps/api/backend";

import createClient from "openapi-fetch";

import { fetchResponseWithTimeout } from "./http.mjs";

export function createApiClient(writeTimeoutMs: number, baseUrl = "") {
  const client = createClient<paths>({
    baseUrl,
    fetch: (request) => fetchResponseWithTimeout(request, writeTimeoutMs),
  });

  return {
    listIats() {
      return client.GET("/iats");
    },

    createSession(request: CreateSessionRequest) {
      return client.POST("/api/sessions", { body: request });
    },

    completeBlock(sessionKey: string, blockIndex: number, request: CompletedBlockRequest) {
      return client.PUT("/api/sessions/{session_key}/blocks/{block_index}", {
        body: request,
        params: {
          path: {
            block_index: blockIndex,
            session_key: sessionKey,
          },
        },
      });
    },

    getScore(sessionKey: string) {
      return client.GET("/api/sessions/{session_key}/score", {
        params: {
          path: {
            session_key: sessionKey,
          },
        },
      });
    },
  };
}

type ApiClient = ReturnType<typeof createApiClient>;

export type ListIatsResult = Awaited<ReturnType<ApiClient["listIats"]>>;
export type CreateSessionResult = Awaited<ReturnType<ApiClient["createSession"]>>;
export type GetScoreResult = Awaited<ReturnType<ApiClient["getScore"]>>;
export type CompleteBlockResult = Awaited<ReturnType<ApiClient["completeBlock"]>>;
