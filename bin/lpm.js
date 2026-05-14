#!/usr/bin/env node
'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const PACKAGE_ROOT = path.resolve(__dirname, '..');
const VENV_PYTHON = process.platform === 'win32'
  ? path.join(PACKAGE_ROOT, '.venv', 'Scripts', 'python.exe')
  : path.join(PACKAGE_ROOT, '.venv', 'bin', 'python');
const LPM_SCRIPT = path.join(PACKAGE_ROOT, 'src', 'LPM.py');

if (!fs.existsSync(VENV_PYTHON)) {
  console.error(
    `\nLPM error: bundled Python venv not found at ${VENV_PYTHON}.\n` +
    'The npm postinstall step did not complete successfully. ' +
    'Re-run `npm install -g @loupeteam/lpm` (or `npm install` in your project) ' +
    'and check the output for the underlying error (commonly: Python 3.8+ is not on PATH).\n'
  );
  process.exit(1);
}

const result = spawnSync(VENV_PYTHON, [LPM_SCRIPT, ...process.argv.slice(2)], {
  stdio: 'inherit',
  shell: false,
});

process.exit(result.status ?? 1);
