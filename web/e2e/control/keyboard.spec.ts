/**
 * The control UI from the keyboard only (plan v4 §7): sign in, make a karaoke, follow it in the
 * jobs, put it on a playlist, reorder, remove and undo, the palette and the cheat sheet, and
 * the time from a key to what it changes on screen (< 100 ms).
 */
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const token = () =>
	readFileSync(fileURLToPath(new URL('./.token', import.meta.url)), 'utf-8').trim();
const MOD = process.platform === 'darwin' ? 'Meta' : 'Control';

/** Milliseconds from pressing `key` to the first change in the DOM that `selector` matches. */
async function responseTime(page: Page, key: string, selector: string): Promise<number> {
	await page.evaluate((sel) => {
		const w = window as unknown as { __t0: number; __t1: number | null };
		w.__t1 = null;
		window.addEventListener('keydown', () => (w.__t0 = performance.now()), {
			once: true,
			capture: true
		});
		const observer = new MutationObserver(() => {
			if (w.__t1 === null && document.querySelector(sel)) {
				w.__t1 = performance.now();
				observer.disconnect();
			}
		});
		observer.observe(document.body, {
			subtree: true,
			childList: true,
			attributes: true,
			characterData: true
		});
	}, selector);
	await page.keyboard.press(key);
	await page.waitForFunction(() => (window as unknown as { __t1: number | null }).__t1 !== null);
	return page.evaluate(() => {
		const w = window as unknown as { __t0: number; __t1: number };
		return w.__t1 - w.__t0;
	});
}

async function signIn(page: Page) {
	await page.goto('/');
	await expect(page.getByLabel('Token de operador')).toBeFocused();
	await page.keyboard.type(token());
	await page.keyboard.press('Enter');
	await expect(page.getByRole('navigation', { name: 'Seccións' })).toBeVisible();
}

test('a karaoke from upload to playlist, from the keyboard', async ({ page }) => {
	await signIn(page);

	// Create: the file comes from the file picker; the rest is keys.
	await page.keyboard.press('g');
	await page.keyboard.press('n');
	await expect(page).toHaveURL(/\/crear$/);
	await expect(page.getByRole('heading', { name: 'Crear' })).toBeVisible();
	await page.getByLabel('Ficheiros de audio ou vídeo').setInputFiles({
		name: 'Proba.mp3',
		mimeType: 'audio/mpeg',
		buffer: Buffer.from('ID3' + '\0'.repeat(4000))
	});
	await page.getByLabel('Título').focus();
	await page.keyboard.type('Proba de teclado');
	await page.keyboard.press(`${MOD}+Enter`);
	await expect(page.getByText('«Proba de teclado» engadido aos traballos')).toBeVisible();

	// The jobs: the fake worker makes it in a few seconds.
	await page.keyboard.press('Escape');
	await page.keyboard.press('g');
	await page.keyboard.press('t');
	await expect(page.getByRole('heading', { name: 'Traballos' })).toBeVisible();
	const job = page.getByRole('row').filter({ hasText: 'Proba de teclado' });
	await expect(job).toBeVisible();
	await expect(job.getByText('Feito')).toBeVisible({ timeout: 60_000 });

	// Its detail, and back.
	await page.keyboard.press('Enter');
	const detail = page.getByRole('complementary', { name: 'Proba de teclado' });
	await expect(detail.getByText('Facer o karaoke')).toBeVisible();
	await page.keyboard.press('Escape');
	await expect(detail).toBeHidden();

	// A playlist, then the song on it.
	await page.keyboard.press('g');
	await page.keyboard.press('d');
	await expect(page.getByRole('region', { name: 'Lista' })).toBeVisible();
	await page.keyboard.press(`${MOD}+Shift+N`);
	await expect(page.getByText('A lista está baleira')).toBeVisible();
	await page.keyboard.press('g');
	await page.keyboard.press('b');
	await expect(page.getByRole('heading', { name: 'Biblioteca' })).toBeVisible();
	const song = page.getByRole('row').filter({ hasText: 'Proba de teclado' });
	await expect(song).toBeVisible();
	await page.keyboard.press('a');
	await page.keyboard.press('a');
	await page.keyboard.press('g');
	await page.keyboard.press('d');
	await expect(page.getByRole('region', { name: 'Lista' })).toBeVisible();
	const items = page.getByRole('region', { name: 'Lista' }).locator('tbody tr');
	await expect(items).toHaveCount(2);

	// Remove one, undo it.
	await page.keyboard.press('Delete');
	await expect(items).toHaveCount(1);
	await page.keyboard.press(`${MOD}+z`);
	await expect(items).toHaveCount(2);

	// The singer, typed in place.
	await page.keyboard.press('s');
	await page.keyboard.type('Uxía');
	await page.keyboard.press('Enter');
	await expect(items.first().getByText('Uxía')).toBeVisible();
});

test('palette, cheat sheet and response times', async ({ page }) => {
	await signIn(page);
	// Once first: the dev server compiles a component the first time it is shown.
	await page.keyboard.press(`${MOD}+k`);
	await page.keyboard.press('Escape');
	await page.keyboard.press('?');
	await page.keyboard.press('Escape');
	const palette = await responseTime(
		page,
		`${MOD}+k`,
		'[role="dialog"][aria-label="Paleta de ordes"]'
	);
	expect(palette).toBeLessThan(100);
	await page.keyboard.type('traballos');
	await page.keyboard.press('Enter');
	await expect(page).toHaveURL(/\/cola$/);

	const sheet = await responseTime(page, '?', '[role="dialog"][aria-label="Atallos de teclado"]');
	expect(sheet).toBeLessThan(100);
	await expect(page.getByRole('dialog').getByText('Reintentar os fallidos')).toBeVisible();
	await page.keyboard.press('Escape');

	await page.keyboard.press('g');
	const navigation = await responseTime(page, 'b', 'input[aria-label^="Buscar por"]');
	expect(navigation).toBeLessThan(100);

	// Every main section passes axe's WCAG 2 A/AA rules.
	for (const path of [
		'/',
		'/directo',
		'/biblioteca',
		'/cola',
		'/equipos',
		'/saidas',
		'/crear',
		'/axustes'
	]) {
		await page.goto(path);
		await expect(page.locator('h1, h2').first()).toBeVisible();
		const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
		expect(
			results.violations.map(
				(v) =>
					`${path}: ${v.id} ${v.nodes.map((n) => n.target.join(' ') + ' ' + (n.failureSummary ?? '')).join(' | ')}`
			)
		).toEqual([]);
	}
});
