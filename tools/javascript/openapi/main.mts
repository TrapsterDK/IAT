import { readFileSync } from "node:fs";
import * as path from "node:path";

import openapiTS, { astToString } from "openapi-typescript";

async function run(schemaPathArg: string | undefined): Promise<void> {
  if (!schemaPathArg) {
    throw new Error("expected one OpenAPI schema path argument");
  }

  const schemaPath = path.resolve(process.cwd(), schemaPathArg);
  const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
  const ast = await openapiTS(schema, {
    alphabetize: true,
    defaultNonNullable: false,
    rootTypes: true,
    rootTypesNoSchemaPrefix: true,
    silent: true,
  });

  process.stdout.write(astToString(ast).trimEnd());
}

run(process.argv[2]).catch((error: unknown) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
});
