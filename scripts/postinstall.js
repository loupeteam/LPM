'use strict';

const { spawnSync } = require('child_process');

const candidates = ['python', 'python3'];
let py = null;

for (const cmd of candidates) {
  const check = spawnSync(cmd, ['-m', 'pip', '--version'], { stdio: 'ignore' });
  if (check.status === 0) {
    py = cmd;
    break;
  }
}

if (!py) {
  console.error(
    '\nLPM postinstall error: Python 3 and pip are required but were not found on PATH.\n' +
    'Please install Python 3 with pip (https://www.python.org/downloads/) and re-run npm install.\n'
  );
  process.exit(1);
}

const result = spawnSync(
  py,
  ['-m', 'pip', 'install', '--user', '-r', 'requirements.txt'],
  { stdio: 'inherit' }
);

process.exit(result.status || 0);
