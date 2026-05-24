import { FETCH_IMAGE_TIMEOUT_MS, IMAGE_MAX_ATTEMPTS, IMAGE_RETRY_DELAY_MS } from "../core/config.mjs";
import { responseErrorMessage } from "../core/errors.mjs";
import { fetchResponseWithTimeout } from "../core/http.mjs";
import { sleep } from "../core/utils.mjs";

export function revokeImageObjectUrls(imageObjectUrls: Map<string, string>) {
  for (const objectUrl of imageObjectUrls.values()) {
    URL.revokeObjectURL(objectUrl);
  }

  imageObjectUrls.clear();
}

export async function ensureImageObjectUrl(sourceUrl: string, imageObjectUrls: Map<string, string>) {
  const cachedObjectUrl = imageObjectUrls.get(sourceUrl);
  if (cachedObjectUrl !== undefined) {
    return cachedObjectUrl;
  }

  const response = await fetchImageResponseWithRetry(sourceUrl);
  const imageBlob = await response.blob();
  const objectUrl = URL.createObjectURL(imageBlob);
  imageObjectUrls.set(sourceUrl, objectUrl);
  return objectUrl;
}

async function fetchImageResponseWithRetry(sourceUrl: string) {
  for (let attemptIndex = 0; attemptIndex < IMAGE_MAX_ATTEMPTS; attemptIndex += 1) {
    try {
      const response = await fetchResponseWithTimeout(new Request(sourceUrl), FETCH_IMAGE_TIMEOUT_MS);
      if (response.ok) {
        return response;
      }

      const errorMessage = await responseErrorMessage(response, `Failed to load image from '${sourceUrl}'.`);

      if (response.status === 408 || response.status === 429 || response.status >= 500) {
        await sleep(IMAGE_RETRY_DELAY_MS * (attemptIndex + 1));
        continue;
      }

      throw new Error(errorMessage);
    } catch (error: unknown) {
      if (attemptIndex < IMAGE_MAX_ATTEMPTS - 1) {
        await sleep(IMAGE_RETRY_DELAY_MS * (attemptIndex + 1));
        continue;
      }

      throw error;
    }
  }

  throw new Error(`Image preload failed for '${sourceUrl}'.`);
}
