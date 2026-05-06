import { existsSync, mkdirSync, renameSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const rootDir = dirname(scriptDir);
const extension = process.platform === 'win32' ? '.exe' : '';
const hostTarget = execSync('rustc --print host-tuple', { cwd: rootDir }).toString().trim();

if (!hostTarget) {
  throw new Error('Failed to resolve Rust host target triple.');
}

const binariesDir = join(rootDir, 'src-tauri', 'binaries');
const sourcePath = join(binariesDir, `smart-move-backend${extension}`);
const targetPath = join(binariesDir, `smart-move-backend-${hostTarget}${extension}`);

mkdirSync(binariesDir, { recursive: true });

if (!existsSync(sourcePath)) {
  throw new Error(`Missing sidecar binary at ${sourcePath}`);
}

if (existsSync(targetPath)) {
  try {
    rmSync(targetPath);
  } catch (error) {
    if (error && typeof error === 'object' && 'code' in error && error.code === 'EPERM') {
      throw new Error(
        `Cannot replace ${targetPath} because it is still in use. Close any running Smart Move/Tauri app, then run the command again.`
      );
    }

    throw error;
  }
}

renameSync(sourcePath, targetPath);
console.log(`Prepared sidecar: ${targetPath}`);
