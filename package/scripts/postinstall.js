#!/usr/bin/env node
"use strict";

// Install the BytePlus binary from the manifest's SG CDN source first, then
// fall back to the matching byteplus-sdk/ark-cli GitHub Release asset. Both
// sources must match the same immutable SHA-256 digest.

const crypto = require("crypto");
const fs = require("fs");
const http = require("http");
const https = require("https");
const path = require("path");
const os = require("os");
const { execFileSync } = require("child_process");
const { Transform, pipeline } = require("stream");

function writeInstallNotice(message, warning = false) {
  const terminal = process.platform === "win32" ? "\\\\.\\CONOUT$" : "/dev/tty";
  let fd = null;
  try {
    fd = fs.openSync(terminal, "w");
    fs.writeSync(fd, `${message}${process.platform === "win32" ? "\r\n" : "\n"}`);
    return;
  } catch (_) {
    (warning ? console.warn : console.log)(message);
  } finally {
    if (fd !== null) {
      try { fs.closeSync(fd); } catch (_) {}
    }
  }
}

function hasInteractiveInstallConsole() {
  if (process.stdout.isTTY || process.stderr.isTTY) return true;
  if (process.platform !== "win32") return false;
  let fd = null;
  try {
    fd = fs.openSync("\\\\.\\CONOUT$", "w");
    return true;
  } catch (_) {
    return false;
  } finally {
    if (fd !== null) {
      try { fs.closeSync(fd); } catch (_) {}
    }
  }
}

const PACKAGE_NAME = "@byteplus/ark-cli";
const GITHUB_RELEASE_PREFIX = "/byteplus-sdk/ark-cli/releases/download/";
const MAX_REDIRECTS = 5;
const MAX_BINARY_BYTES = 256 * 1024 * 1024;
const DEFAULT_DOWNLOAD_TIMEOUT_MS = 30_000;

if (process.env.ARKCLI_SKIP_POSTINSTALL === "1") {
  process.exit(0);
}

const platformMap = { darwin: "darwin", linux: "linux", win32: "windows" };
const archMap = { x64: "amd64", arm64: "arm64" };
const platform = platformMap[process.platform];
const arch = archMap[process.arch];
if (!platform || !arch) {
  console.error(`${PACKAGE_NAME}: unsupported platform ${process.platform}-${process.arch}`);
  process.exit(1);
}

// Snapshot product state before bootstrap or the downloaded binary can create
// it. Any lookup failure is historical/ambiguous and therefore not fresh.
let freshStateAbsent = false;
try {
  const home = os.homedir();
  freshStateAbsent = home !== "" && !fs.existsSync(path.join(home, ".arkcli-bp"));
} catch (_) {}

function readJSON(file, label) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (err) {
    throw new Error(`cannot read ${label}: ${err.message || err}`);
  }
}

const packageRoot = path.join(__dirname, "..");
let packageJSON;
let manifest;
try {
  packageJSON = readJSON(path.join(packageRoot, "package.json"), "package.json");
  manifest = readJSON(path.join(packageRoot, "manifest.json"), "manifest.json");
} catch (err) {
  console.error(`${PACKAGE_NAME}: ${err.message || err}`);
  process.exit(1);
}

const stableVersionPattern =
  /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/;
const probeVersionPattern =
  /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-probe\.[0-9a-f]{12}$/;
const prereleaseVersionPattern =
  /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-prerelease\.[0-9a-f]{12}$/;
const packageVersion = packageJSON.version || "";
const isProbe = probeVersionPattern.test(packageVersion);
const isPrerelease = prereleaseVersionPattern.test(packageVersion);
const isNonStable = isProbe || isPrerelease;
if (
  packageJSON.name !== PACKAGE_NAME ||
  (!stableVersionPattern.test(packageVersion) && !isNonStable)
) {
  console.error(`${PACKAGE_NAME}: package identity is missing or malformed`);
  process.exit(1);
}
if (manifest.package !== PACKAGE_NAME || manifest.version !== packageJSON.version) {
  console.error(
    `${PACKAGE_NAME}: manifest identity mismatch (package=${manifest.package || "<missing>"}, version=${manifest.version || "<missing>"})`,
  );
  process.exit(1);
}

const key = `${platform}-${arch}`;
const entry = manifest.platforms && manifest.platforms[key];
if (!entry || entry.kind !== "cdn" || typeof entry.url !== "string") {
  console.error(`${PACKAGE_NAME}: manifest has no CDN binary entry for ${key}`);
  process.exit(1);
}
if (!/^[0-9a-f]{64}$/i.test(entry.sha256 || "")) {
  console.error(`${PACKAGE_NAME}: manifest has a missing or malformed sha256 for ${key}`);
  process.exit(1);
}
if (isNonStable) {
  if (Object.prototype.hasOwnProperty.call(entry, "fallback")) {
    console.error(`${PACKAGE_NAME}: non-stable manifest must not claim a GitHub Release fallback for ${key}`);
    process.exit(1);
  }
} else {
  if (
    !entry.fallback ||
    entry.fallback.kind !== "github-release" ||
    typeof entry.fallback.url !== "string"
  ) {
    console.error(`${PACKAGE_NAME}: manifest has no GitHub Release fallback for ${key}`);
    process.exit(1);
  }
}

const allowTestHTTP = process.env.ARKCLI_POSTINSTALL_ALLOW_HTTP_FOR_TESTS === "1";
const testTimeout = Number(process.env.ARKCLI_POSTINSTALL_TIMEOUT_MS_FOR_TESTS || 0);
const downloadTimeoutMS =
  allowTestHTTP && Number.isInteger(testTimeout) && testTimeout >= 50 && testTimeout <= 30_000
    ? testTimeout
    : DEFAULT_DOWNLOAD_TIMEOUT_MS;

function isLoopback(hostname) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

function checkedURL(raw, kind, initial) {
  let parsed;
  try {
    parsed = new URL(raw);
  } catch (err) {
    throw new Error(`${kind} URL is malformed: ${err.message || err}`);
  }
  if (parsed.username || parsed.password) {
    throw new Error(`${kind} URL must not contain credentials`);
  }
  const testLoopback =
    allowTestHTTP && parsed.protocol === "http:" && isLoopback(parsed.hostname);
  if (parsed.protocol !== "https:") {
    if (!testLoopback) {
      throw new Error(`${kind} URL is rejected: HTTPS is required`);
    }
  }
  if (
    initial &&
    kind === "github-release" &&
    !testLoopback &&
    (parsed.hostname !== "github.com" || !parsed.pathname.startsWith(GITHUB_RELEASE_PREFIX))
  ) {
    throw new Error(`${kind} URL must target byteplus-sdk/ark-cli releases`);
  }
  return parsed;
}

function download(
  rawURL,
  destination,
  kind,
  redirects = 0,
  deadline = Date.now() + downloadTimeoutMS,
) {
  if (redirects > MAX_REDIRECTS) {
    return Promise.reject(new Error(`${kind} exceeded ${MAX_REDIRECTS} redirects`));
  }
  const remaining = deadline - Date.now();
  if (remaining <= 0) {
    return Promise.reject(new Error(`${kind} exceeded the total download deadline`));
  }
  let parsed;
  try {
    parsed = checkedURL(rawURL, kind, redirects === 0);
  } catch (err) {
    return Promise.reject(err);
  }

  return new Promise((resolve, reject) => {
    let settled = false;
    let activeResponse = null;
    let wallTimer = null;
    const resolveOnce = (value) => {
      if (settled) return;
      settled = true;
      if (wallTimer !== null) clearTimeout(wallTimer);
      resolve(value);
    };
    const rejectOnce = (err) => {
      if (settled) return;
      settled = true;
      if (wallTimer !== null) clearTimeout(wallTimer);
      reject(err);
    };
    const transport = parsed.protocol === "http:" ? http : https;
    const request = transport.get(parsed, (response) => {
      activeResponse = response;
      if (
        response.statusCode >= 300 &&
        response.statusCode < 400 &&
        response.headers.location
      ) {
        let next;
        try {
          next = new URL(response.headers.location, parsed).toString();
        } catch (err) {
          response.destroy();
          rejectOnce(new Error(`${kind} redirect URL is malformed: ${err.message || err}`));
          return;
        }
        response.destroy();
        resolveOnce(download(next, destination, kind, redirects + 1, deadline));
        return;
      }
      if (response.statusCode !== 200) {
        response.destroy();
        rejectOnce(new Error(`HTTP ${response.statusCode} for ${kind}`));
        return;
      }

      const declaredLength = Number(response.headers["content-length"] || 0);
      if (declaredLength > MAX_BINARY_BYTES) {
        response.destroy();
        rejectOnce(new Error(`${kind} binary exceeds ${MAX_BINARY_BYTES} bytes`));
        return;
      }

      let received = 0;
      const limiter = new Transform({
        transform(chunk, encoding, callback) {
          received += chunk.length;
          if (received > MAX_BINARY_BYTES) {
            callback(new Error(`${kind} binary exceeds ${MAX_BINARY_BYTES} bytes`));
            return;
          }
          callback(null, chunk);
        },
      });
      const output = fs.createWriteStream(destination, { flags: "wx", mode: 0o600 });
      pipeline(response, limiter, output, (err) => {
        const settleAfterOutputClose = () => {
          if (err) {
            rejectOnce(err);
          } else if (received === 0) {
            rejectOnce(new Error(`${kind} returned an empty binary`));
          } else {
            resolveOnce();
          }
        };
        if (output.closed) {
          settleAfterOutputClose();
          return;
        }
        // On Windows, pipeline's callback can run before the underlying file
        // handle has emitted close. Do not let the fallback remove or reuse the
        // abandoned destination until the OS has released that handle.
        output.once("close", settleAfterOutputClose);
      });
    });
    wallTimer = setTimeout(() => {
      const err = new Error(`${kind} exceeded the total download deadline`);
      if (activeResponse !== null) {
        // The pipeline callback owns settlement after a response has started.
        // Waiting for it guarantees the destination stream is closed before the
        // caller removes the abandoned file, which Windows requires.
        activeResponse.destroy(err);
        request.destroy(err);
        return;
      }
      request.destroy(err);
      rejectOnce(err);
    }, remaining);
    request.setTimeout(Math.min(DEFAULT_DOWNLOAD_TIMEOUT_MS, remaining), () => {
      request.destroy(new Error(`${kind} download timed out`));
    });
    request.on("error", (err) => {
      if (activeResponse !== null) return;
      rejectOnce(err);
    });
  });
}

function sha256(file) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash("sha256");
    const input = fs.createReadStream(file);
    input.on("error", reject);
    hash.on("error", reject);
    hash.on("finish", () => resolve(hash.digest("hex")));
    input.pipe(hash);
  });
}

async function downloadVerifiedBinary(sources, destination, expectedSHA) {
  const errors = [];
  for (const source of sources) {
    fs.rmSync(destination, { force: true });
    try {
      console.log(`${PACKAGE_NAME}: downloading ${key} binary from ${source.kind}...`);
      await download(source.url, destination, source.kind);
      const actual = await sha256(destination);
      if (actual !== expectedSHA.toLowerCase()) {
        throw new Error(`sha256 mismatch (expected ${expectedSHA}, actual ${actual})`);
      }
      return source;
    } catch (err) {
      fs.rmSync(destination, { force: true });
      const detail = err.message || String(err);
      errors.push(`${source.kind}: ${detail}`);
      console.warn(`${PACKAGE_NAME}: ${source.kind} binary source failed: ${detail}`);
    }
  }
  throw new Error(errors.join("; "));
}

function recoverInterruptedInstall(binary, backup) {
  if (!fs.existsSync(backup)) {
    return;
  }
  if (fs.existsSync(binary)) {
    fs.rmSync(backup, { force: true });
  } else {
    fs.renameSync(backup, binary);
  }
}

async function install() {
  const ext = platform === "windows" ? ".exe" : "";
  const binDir = path.join(packageRoot, "bin");
  const binPath = path.join(binDir, `arkcli-${platform}-${arch}${ext}`);
  const tempPath = `${binPath}.download-${process.pid}`;
  const backupPath = `${binPath}.backup`;
  const injectedFailure = allowTestHTTP
    ? process.env.ARKCLI_POSTINSTALL_FAIL_STEP_FOR_TESTS || ""
    : "";
  const failStepForTests = (step) => {
    if (injectedFailure === step) {
      throw new Error(`injected ${step} failure`);
    }
  };
  fs.mkdirSync(binDir, { recursive: true });
  recoverInterruptedInstall(binPath, backupPath);

  let installedFrom;
  try {
    const sources = [{ kind: "cdn", url: entry.url }];
    if (!isNonStable) {
      sources.push({ kind: "github-release", url: entry.fallback.url });
    }
    installedFrom = await downloadVerifiedBinary(
      sources,
      tempPath,
      entry.sha256,
    );
  } catch (err) {
    fs.rmSync(tempPath, { force: true });
    throw new Error(`binary download failed: ${err.message || err}`);
  }

  let oldMoved = false;
  let newInstalled = false;
  try {
    if (platform !== "windows") {
      failStepForTests("chmod-temp");
      fs.chmodSync(tempPath, 0o755);
    }
    if (fs.existsSync(binPath)) {
      failStepForTests("move-old");
      fs.renameSync(binPath, backupPath);
      oldMoved = true;
    }
    failStepForTests("install-new");
    fs.renameSync(tempPath, binPath);
    newInstalled = true;
    fs.rmSync(backupPath, { force: true });
  } catch (err) {
    fs.rmSync(tempPath, { force: true });
    if (newInstalled) {
      fs.rmSync(binPath, { force: true });
    }
    if (oldMoved && fs.existsSync(backupPath)) {
      fs.renameSync(backupPath, binPath);
    }
    throw new Error(`cannot install verified binary: ${err.message || err}`);
  }

  console.log(`${PACKAGE_NAME}: installed ${path.basename(binPath)} from ${installedFrom.kind}`);

  if (process.env.CI || process.env.BUILD_NUMBER || process.env.RUN_ID) {
    return;
  }

  if (process.env.npm_config_global === "true") {
    // Enrollment publishes only inert exact-install evidence. Active consent
    // can be created only by later successful human CLI invocations.
    let bootstrapReady = process.platform !== "win32";
    let bootstrapError;
    if (process.platform === "win32") {
      try {
        execFileSync(binPath, ["_initialize-update-bootstrap"], {
          timeout: 120000,
          stdio: "ignore",
        });
        bootstrapReady = true;
      } catch (err) {
        bootstrapError = err;
      }
    }
    let automaticSupported;
    let mode;
    let enrollmentPhase;
    let policyError;
    if (bootstrapReady) {
      try {
        const supported = execFileSync(
          binPath,
          ["_refresh-update-cache", "--print-automatic-supported"],
          { timeout: 10000, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
        ).trim();
        if (supported !== "true" && supported !== "false") {
          throw new Error(`unexpected automatic-update capability ${JSON.stringify(supported)}`);
        }
        automaticSupported = supported === "true";
        if (automaticSupported) {
          enrollmentPhase = execFileSync(
            binPath,
            [
              "_refresh-update-cache", "--initialize-enrollment",
              `--fresh-state-absent=${freshStateAbsent}`,
            ],
            { timeout: 10000, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
          ).trim();
          if (![
            "disabled",
            "fresh_pending",
            "grace_completed",
            "automatic_active",
            "manual_reinstall_suspended",
          ].includes(enrollmentPhase)) {
            throw new Error(`unexpected automatic-update enrollment phase ${JSON.stringify(enrollmentPhase)}`);
          }
          mode = execFileSync(
            binPath,
            ["_refresh-update-cache", "--print-mode"],
            { timeout: 10000, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
          ).trim();
        }
      } catch (err) {
        policyError = err;
      }
    }
    try {
      execFileSync(binPath, ["_refresh-update-cache"], {
        timeout: 10000,
        stdio: "ignore",
      });
    } catch (_) {}
    if (bootstrapError) {
      writeInstallNotice(
        `${PACKAGE_NAME}: recoverable automatic-update bootstrap is unavailable; this install remains notice/manual-only (${bootstrapError.message || bootstrapError})`,
        true,
      );
    } else if (policyError) {
      writeInstallNotice(
        `${PACKAGE_NAME}: automatic-update capability could not be confirmed; this install remains notice/manual-only (${policyError.message || policyError})`,
        true,
      );
    } else if (automaticSupported === false) {
      writeInstallNotice(`${PACKAGE_NAME}: update notices/manual update remain active by default; silent automatic update is not enabled for this product and platform.`);
    } else if (enrollmentPhase === "fresh_pending") {
      writeInstallNotice(`${PACKAGE_NAME}: silent stable patch updates are enabled by default for this new install; the first successful eligible human business command may schedule a background update. Disable with \`arkcli config set update.mode disabled\`.`);
    } else if (enrollmentPhase === "manual_reinstall_suspended") {
      writeInstallNotice(`${PACKAGE_NAME}: a manual npm install or version change was detected, so silent automatic updates are paused. Keep this version with \`arkcli config set update.mode disabled\`; resume with \`arkcli config set update.mode automatic\`.`);
    } else if (enrollmentPhase === "disabled" || mode === "disabled" || mode === "notify") {
      if (mode === "notify") {
        writeInstallNotice(`${PACKAGE_NAME}: the legacy notify-only update policy was preserved; silent automatic update is not active. Resume with \`arkcli config set update.mode automatic\`.`);
      } else {
        writeInstallNotice(`${PACKAGE_NAME}: the disabled update policy was preserved; update notices remain active and silent automatic update is not active.`);
      }
    } else if (enrollmentPhase === "grace_completed") {
      writeInstallNotice(`${PACKAGE_NAME}: a legacy first-run grace state was detected; the next successful eligible human business command may activate consent and schedule a background update. Disable with \`arkcli config set update.mode disabled\`.`);
    } else if (enrollmentPhase === "automatic_active") {
      writeInstallNotice(`${PACKAGE_NAME}: silent stable patch update consent remains active for this exact install. Disable with \`arkcli config set update.mode disabled\`.`);
    }
  }

  let tty = null;
  try {
    tty = fs.openSync("/dev/tty", "r+");
  } catch (_) {
    // A controlling terminal is optional; +connect is still non-interactive.
  }
  const stdio = tty === null ? "inherit" : ["ignore", tty, tty];
  try {
    execFileSync(binPath, ["+connect", "--refresh"], { stdio });
  } catch (err) {
    const message =
      `${PACKAGE_NAME}: Skill sync skipped (${err.message || err}). ` +
      "Run `arkcli +connect --refresh` to retry.";
    if (tty === null) {
      console.warn(message);
    } else {
      try {
        fs.writeSync(tty, `${message}\n`);
      } catch (_) {}
    }
  } finally {
    if (tty !== null) {
      try {
        fs.closeSync(tty);
      } catch (_) {}
    }
  }
}

install().catch((err) => {
  console.error(`${PACKAGE_NAME}: ${err.message || err}`);
  process.exit(1);
});
