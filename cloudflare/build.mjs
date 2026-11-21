// Cloudflare Workers Builds: install and compile the existing React/Vite app.
// Does not modify source code or replace the Python backend.
import { existsSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';

const repo = resolve(import.meta.dirname, '..');
const frontend = join(repo, 'frontend');
const manifest = join(frontend, 'package.json');
const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';

if (!existsSync(manifest)) {
  throw new Error('Missing frontend/package.json. Run this from the complete SocietyOS repository.');
}
const pkg = JSON.parse(readFileSync(manifest, 'utf8'));
if (!pkg.scripts?.build) {
  throw new Error('frontend/package.json must define a build script.');
}

const hasLock = existsSync(join(frontend, 'package-lock.json'));
const args = hasLock ? ['ci', '--no-audit', '--no-fund'] : ['install', '--no-audit', '--no-fund'];
console.log(`Installing frontend packages with npm ${args[0]}...`);
execFileSync(npm, args, {cwd: frontend, stdio: 'inherit'});
console.log('Building React frontend...');
execFileSync(npm, ['run', 'build'], {cwd: frontend, stdio: 'inherit'});
if (!existsSync(join(frontend, 'dist', 'index.html'))) {
  throw new Error('Expected frontend/dist/index.html after build. Check Vite outDir.');
}
console.log('Frontend ready at frontend/dist. Cloudflare can deploy these static assets.');
console.log('Note: the FastAPI backend is NOT deployed by this command.');
