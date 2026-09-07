#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const PACKAGE_NAME = "@byteplus/ark-cli";
const platformMap = { darwin: "darwin", linux: "linux", win32: "windows" };
const archMap = { x64: "amd64", arm64: "arm64" };
const platform = platformMap[process.platform];
const arch = archMap[process.arch];

if (!platform || !arch) {
  console.error(`${PACKAGE_NAME}: unsupported platform ${process.platform}-${process.arch}`);
  process.exit(1);
}

const ext = platform === "windows" ? ".exe" : "";
const binary = path.join(__dirname, "..", "bin", `arkcli-${platform}-${arch}${ext}`);

let binaryReady = false;
try {
  const info = fs.lstatSync(binary);
  binaryReady = info.isFile() && !info.isSymbolicLink();
} catch (_) {
  // The repair guidance below covers missing and unreadable binaries.
}

if (!binaryReady) {
  console.error(
    `${PACKAGE_NAME}: binary not found at ${binary}\n` +
      `Reinstall the package with:\n  npm install -g ${PACKAGE_NAME}\n` +
      `or retry the install step with:\n  node ${path.join(__dirname, "postinstall.js")}`,
  );
  process.exit(1);
}

try {
  execFileSync(binary, process.argv.slice(2), { stdio: "inherit" });
} catch (err) {
  if (err.signal) process.kill(process.pid, err.signal);
  process.exit(Number.isInteger(err.status) ? err.status : 1);
}
