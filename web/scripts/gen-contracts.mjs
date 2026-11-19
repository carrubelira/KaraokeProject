// Generates the TS types in src/lib/contracts/generated/ from every schema in ../schemas
// (`pnpm gen:contracts`, run by `make contracts`).
import { readdirSync, writeFileSync } from 'node:fs';
import { compileFromFile } from 'json-schema-to-typescript';

const banner = '/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */';
const skip = new Set(['openapi.json']);
for (const file of readdirSync('../schemas').sort()) {
	if (!file.endsWith('.schema.json') || skip.has(file)) continue;
	const name = file.replace('.schema.json', '');
	const ts = await compileFromFile(`../schemas/${file}`, {
		bannerComment: banner,
		additionalProperties: false,
		unknownAny: true,
		ignoreMinAndMaxItems: true,
		style: { useTabs: true, singleQuote: true }
	});
	writeFileSync(`src/lib/contracts/generated/${name}.ts`, ts);
	console.log(`src/lib/contracts/generated/${name}.ts`);
}
