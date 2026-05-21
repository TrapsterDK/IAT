import { createServer, type IncomingMessage, type RequestListener, type ServerResponse } from "node:http";

export interface TestHttpServer {
  close: () => Promise<void>;
  url: string;
}

export async function listen(
  handler: RequestListener<typeof IncomingMessage, typeof ServerResponse>,
): Promise<TestHttpServer> {
  const server = createServer(handler);
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      resolve();
    });
  });

  const address = server.address();
  if (address === null || typeof address === "string") {
    throw new Error("Expected an IPv4 test server address.");
  }

  return {
    close: async () => {
      if (!server.listening) {
        return;
      }

      await new Promise<void>((resolve, reject) => {
        server.close((error?: Error) => {
          if (error) {
            reject(error);
            return;
          }

          resolve();
        });
      });
    },
    url: `http://127.0.0.1:${address.port}`,
  };
}
