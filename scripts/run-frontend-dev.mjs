import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const rootDir = dirname(scriptDir);
const frontendDir = join(rootDir, 'frontend');
const command = process.platform === 'win32' ? 'cmd.exe' : 'npm';
const args = process.platform === 'win32'
  ? ['/d', '/s', '/c', 'npm run dev']
  : ['run', 'dev'];

const child = spawn(command, args, {
  cwd: frontendDir,
  stdio: 'inherit',
  shell: false,
  env: {
    ...process.env,
    INIT_CWD: frontendDir,
  },
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});
