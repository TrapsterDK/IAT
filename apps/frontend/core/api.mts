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
      return client.GET("/api/iats");
    },

    getIat(slug: string) {
      return client.GET("/api/iats/{slug}", {
        params: {
          path: {
            slug,
          },
        },
      });
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

export type ApiClient = ReturnType<typeof createApiClient>;
