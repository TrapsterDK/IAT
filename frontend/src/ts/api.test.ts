import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchWithTimeout } from "./api";

describe("fetchWithTimeout", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("aborts stalled requests after 10 seconds", async () => {
    vi.useFakeTimers();

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((_input, init) => {
      const signal = init?.signal;

      return new Promise<Response>((_resolve, reject) => {
        signal?.addEventListener("abort", () => {
          reject(new DOMException("The operation was aborted.", "AbortError"));
        });
      });
    });

    const responsePromise = fetchWithTimeout("/api/tests", undefined, {
      timeout: "Timed out.",
    });
    const rejectionExpectation = expect(responsePromise).rejects.toThrowError("Timed out.");

    await vi.advanceTimersByTimeAsync(10_000);

    await rejectionExpectation;
    expect(fetchSpy).toHaveBeenCalledOnce();
  });

  it("returns the response before the timeout when fetch succeeds", async () => {
    const response = new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(response);

    await expect(fetchWithTimeout("/api/tests")).resolves.toBe(response);
    expect(fetchSpy).toHaveBeenCalledOnce();
  });
});
