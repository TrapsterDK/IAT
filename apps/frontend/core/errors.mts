type ApiErrorLike = {
  error?: unknown;
  response: Response;
};

export async function apiErrorMessage(error: ApiErrorLike, fallbackMessage: string) {
  if (typeof error.error === "object" && error.error !== null && "detail" in error.error) {
    const detail = (error.error as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail !== "") {
      return detail;
    }
  }

  return responseErrorMessage(error.response, fallbackMessage);
}

export async function responseErrorMessage(response: Response, fallbackMessage: string) {
  const responseText = (await response.text()).trim();
  if (responseText !== "") {
    try {
      const parsedPayload = JSON.parse(responseText) as { detail?: unknown };
      if (typeof parsedPayload.detail === "string" && parsedPayload.detail !== "") {
        return parsedPayload.detail;
      }
    } catch {
      return responseText;
    }

    return responseText;
  }

  return response.statusText || fallbackMessage;
}

export function unknownErrorMessage(error: unknown) {
  if (typeof error === "string" && error !== "") {
    return error;
  }

  if (error instanceof Error && error.message !== "") {
    return error.message;
  }

  return "An unexpected error occurred.";
}
