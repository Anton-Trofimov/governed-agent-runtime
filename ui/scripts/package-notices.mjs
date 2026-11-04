import { copyFileSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const ui = new URL('../', import.meta.url);
for (const name of ['LICENSE', 'NOTICE']) {
  copyFileSync(new URL(`../${name}`, ui), new URL(`dist/${name}`, ui));
}
// Runtime bundle dependencies, including react-dom's scheduler. Build tools
// are not distributed. Keep this list aligned with the runtime bundle.
const packages = ['react', 'react-dom', 'scheduler', 'zod'];
const notices = packages.map(name => {
  const directory = new URL(`node_modules/${name}/`, ui);
  const pkg = JSON.parse(readFileSync(new URL('package.json', directory), 'utf8'));
  const license = readFileSync(new URL('LICENSE', directory), 'utf8');
  return `${name} ${pkg.version}\n${'='.repeat(60)}\n${license}`;
});
writeFileSync(fileURLToPath(new URL('dist/THIRD-PARTY-NOTICES.txt', ui)), notices.join('\n\n'));
