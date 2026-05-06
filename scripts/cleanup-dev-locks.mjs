import { execFileSync } from 'node:child_process';

if (process.platform !== 'win32') {
  process.exit(0);
}

const processNames = [
  'smart-move-backend-x86_64-pc-windows-msvc.exe',
  'smart-move-backend.exe',
  'smart_move_desktop.exe',
];

for (const processName of processNames) {
  try {
    execFileSync('taskkill', ['/F', '/IM', processName], { stdio: 'ignore' });
  } catch {
  }
}

try {
  const output = execFileSync('netstat', ['-ano', '-p', 'tcp'], { encoding: 'utf8' });
  const lines = output.split(/\r?\n/);
  const pids = new Set();

  for (const line of lines) {
    if (!line.includes(':3000') && !line.includes(':3001')) {
      continue;
    }

    const match = line.trim().match(/^TCP\s+\S+:(3000|3001)\s+\S+\s+LISTENING\s+(\d+)$/i);
    if (match) {
      pids.add(match[2]);
    }
  }

  for (const pid of pids) {
    try {
      execFileSync('taskkill', ['/F', '/PID', pid], { stdio: 'ignore' });
    } catch {
    }
  }
} catch {
}
