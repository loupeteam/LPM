#!/usr/bin/env node
'use strict';

const { spawnSync } = require('child_process');
const path = require('path');

const lpmScript = path.join(__dirname, '..', 'src', 'LPM.py');
const python = process.platform === 'win32' ? 'python' : 'python3';

const result = spawnSync(python, [lpmScript, ...process.argv.slice(2)], {
  stdio: 'inherit',
  shell: false,
});

process.exit(result.status ?? 1);
