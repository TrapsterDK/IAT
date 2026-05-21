export function fetchResponseWithTimeout(request: Request, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => {
    controller.abort(new Error("The request timed out."));
  }, timeoutMs);

  return fetch(request, { signal: controller.signal }).finally(() => {
    globalThis.clearTimeout(timeoutId);
  });
}
