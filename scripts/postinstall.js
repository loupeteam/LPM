'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const PACKAGE_ROOT = path.resolve(__dirname, '..');
const VENV_DIR = path.join(PACKAGE_ROOT, '.venv');
const REQUIREMENTS = path.join(PACKAGE_ROOT, 'requirements.txt');
const ASPYTHON_DIR = path.join(PACKAGE_ROOT, 'src', 'ASPython');
const MIN_PY = [3, 8];

function pickPythonLauncher() {
  // [command, [...args], pretty]
  const candidates = process.platform === 'win32'
    ? [['py', ['-3'], 'py -3'], ['python', [], 'python'], ['python3', [], 'python3']]
    : [['python3', [], 'python3'], ['python', [], 'python']];

  const probe = '__import__("sys").stdout.write("{}.{}".format(*__import__("sys").version_info[:2]))';
  for (const [cmd, args, pretty] of candidates) {
    const r = spawnSync(cmd, [...args, '-c', probe], { encoding: 'utf8' });
    if (r.status !== 0 || !r.stdout) continue;
    const [maj, min] = r.stdout.trim().split('.').map(Number);
    if (maj > MIN_PY[0] || (maj === MIN_PY[0] && min >= MIN_PY[1])) {
      return { cmd, args, pretty, version: `${maj}.${min}` };
    }
  }
  return null;
}

function venvPython() {
  return process.platform === 'win32'
    ? path.join(VENV_DIR, 'Scripts', 'python.exe')
    : path.join(VENV_DIR, 'bin', 'python');
}

function run(cmd, args, label) {
  const r = spawnSync(cmd, args, { stdio: 'inherit' });
  if (r.status !== 0) {
    console.error(`\nLPM postinstall: ${label} failed (exit ${r.status}).`);
    process.exit(r.status || 1);
  }
}

const launcher = pickPythonLauncher();
if (!launcher) {
  console.error(
    `\nLPM postinstall error: Python ${MIN_PY[0]}.${MIN_PY[1]}+ is required but was not found on PATH.\n` +
    'Install Python 3 (https://www.python.org/downloads/) and re-run `npm install`.\n'
  );
  process.exit(1);
}

if (!fs.existsSync(path.join(ASPYTHON_DIR, 'pyproject.toml'))) {
  console.error(
    `\nLPM postinstall error: bundled ASPython package not found at ${ASPYTHON_DIR}.\n` +
    'If you are installing from a git clone, run `git submodule update --init` and try again.\n'
  );
  process.exit(1);
}

console.log(`LPM postinstall: using ${launcher.pretty} (Python ${launcher.version}); creating venv at ${VENV_DIR}`);
run(launcher.cmd, [...launcher.args, '-m', 'venv', VENV_DIR], 'venv creation');

const py = venvPython();
run(py, ['-m', 'pip', 'install', '--upgrade', 'pip'], 'pip upgrade');
run(py, ['-m', 'pip', 'install', '-r', REQUIREMENTS], 'requirements install');
run(py, ['-m', 'pip', 'install', ASPYTHON_DIR], 'aspython install');

console.log('LPM postinstall: complete.');
