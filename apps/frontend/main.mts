import type { CreateSessionRequest, SessionBootstrapResponse } from "@iat/apps/api/backend";

type ExamplePayload = CreateSessionRequest & {
  readonly iat_slug: string;
};

type SessionKey = SessionBootstrapResponse["session_key"];

export function createSessionPayload(iatSlug: string): ExamplePayload {
  return {
    iat_slug: iatSlug,
  };
}

export function sessionKey(response: SessionBootstrapResponse): SessionKey {
  return response.session_key;
}
