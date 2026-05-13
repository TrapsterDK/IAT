import { copyFileSync, existsSync, mkdirSync, mkdtempSync } from "node:fs";
import { spawnSync } from "node:child_process";
import * as os from "node:os";
import * as path from "node:path";

function resolveArg(arg) {
  return path.resolve(process.cwd(), arg);
}

function createTempDir(prefix) {
  const baseDir = process.env.TEST_TMPDIR ?? process.env.TMPDIR ?? os.tmpdir();
  mkdirSync(baseDir, { recursive: true });
  return mkdtempSync(path.join(baseDir, prefix));
}

function prepareVerifyProjectDir(packageJson, lockfile) {
  const dir = createTempDir("pnpm-lock-");

  copyFileSync(packageJson, path.join(dir, "package.json"));
  copyFileSync(lockfile, path.join(dir, "pnpm-lock.yaml"));

  const npmrc = path.join(path.dirname(packageJson), ".npmrc");
  if (existsSync(npmrc)) {
    copyFileSync(npmrc, path.join(dir, ".npmrc"));
  }

  return dir;
}

function run(mode, pnpmArg, packageJsonArg, lockfileArg) {
  const pnpm = resolveArg(pnpmArg);
  const packageJson = resolveArg(packageJsonArg);
  const lockfile = resolveArg(lockfileArg);

  let dir;
  if (mode === "generate") {
    const workspaceDir = process.env.BUILD_WORKSPACE_DIRECTORY;
    if (!workspaceDir) {
      throw new Error("BUILD_WORKSPACE_DIRECTORY must be set for lock generation");
    }
    dir = workspaceDir;
  } else if (mode === "verify") {
    dir = prepareVerifyProjectDir(packageJson, lockfile);
  } else {
    throw new Error(`unknown mode: ${mode}`);
  }

  if (path.dirname(packageJson) !== path.dirname(lockfile)) {
    throw new Error("package.json and pnpm-lock.yaml must be in the same directory");
  }

  const env = {
    ...process.env,
    BAZEL_BINDIR: process.env.BAZEL_BINDIR ?? ".",
    npm_config_manage_package_manager_versions: "false",
  };

  if (mode === "verify") {
    const pnpmHome = createTempDir("pnpm-home-");
    const pnpmStoreDir = path.join(pnpmHome, "store");

    mkdirSync(pnpmStoreDir, { recursive: true });

    env.HOME = pnpmHome;
    env.XDG_CACHE_HOME = pnpmHome;
    env.XDG_DATA_HOME = pnpmHome;
    env.XDG_STATE_HOME = pnpmHome;
    env.npm_config_store_dir = pnpmStoreDir;
  }

  const args = ["install", "--dir", dir, "--lockfile-dir", dir, "--lockfile-only", "--ignore-scripts"];

  if (mode === "verify") {
    args.splice(1, 0, "--frozen-lockfile");
  }

  const result = spawnSync(pnpm, args, {
    cwd: dir,
    env,
    stdio: "inherit",
  });

  if (result.error) {
    throw result.error;
  }

  process.exit(result.status ?? 1);
}

run(process.argv[2], process.argv[3], process.argv[4], process.argv[5]);
