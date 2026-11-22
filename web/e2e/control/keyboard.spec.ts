/**
 * The console from the keyboard (plan v4 §7): sign in, add a song (analysed, then reviewed),
 * follow it in Jobs, queue it twice on a screen, remove and undo, the palette and the cheat
 * sheet, and the time from a key to what it changes on screen (< 100 ms).
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
	await expect(page.getByRole('navigation', { name: 'Menú principal' })).toBeVisible();
}

test('a song from upload to a screen queue, from the keyboard', async ({ page }) => {
	await signIn(page);

	// Add: the file comes from the file picker; it is analysed at once.
	await page.keyboard.press('g');
	await page.keyboard.press('n');
	await expect(page).toHaveURL(/\/engadir$/);
	await expect(page.getByRole('heading', { name: 'Engadir canción' })).toBeVisible();
	await page.locator('input[type="file"]').setInputFiles({
		name: 'Proba.mp3',
		mimeType: 'audio/mpeg',
		buffer: Buffer.from('ID3' + '\0'.repeat(4000))
	});

	// The review: what the analysis found, corrected before anything heavy runs.
	await expect(page.getByRole('heading', { name: 'Revisar os datos da canción' })).toBeVisible({
		timeout: 30_000
	});
	const title = page.getByLabel('Título');
	await title.fill('Proba de teclado');
	await page.getByLabel('Pegar a letra a man').check();
	await page.getByRole('textbox', { name: 'Pegar a letra a man' }).fill('la la la');
	await title.focus();
	await page.keyboard.press('Enter');
	await expect(page.getByText('Creando o karaoke de «Proba de teclado»')).toBeVisible();

	// Jobs: the fake worker makes it in a few seconds.
	await page.keyboard.press('Escape');
	await page.keyboard.press('g');
	await page.keyboard.press('p');
	await expect(page.getByRole('heading', { name: 'Procesamento' })).toBeVisible();
	const job = page.locator('tr.job').filter({ hasText: 'Proba de teclado' });
	await expect(job.getByText('Rematado')).toBeVisible({ timeout: 60_000 });

	// The library: A puts it in the screen's queue, twice.
	await page.keyboard.press('g');
	await page.keyboard.press('b');
	await expect(page.getByRole('heading', { name: 'Biblioteca' })).toBeVisible();
	await expect(page.locator('tbody tr').filter({ hasText: 'Proba de teclado' })).toBeVisible();
	await page.keyboard.press('a');
	await expect(page.getByText('«Proba de teclado» engadida á cola de sala')).toBeVisible();
	await page.keyboard.press('a');

	// Playback: the queue, Delete removes, Mod+Z puts it back.
	await page.keyboard.press('g');
	await page.keyboard.press('r');
	const items = page.locator('table.queue tbody tr').filter({ hasText: 'Proba de teclado' });
	await expect(items).toHaveCount(2);
	await page.keyboard.press('Delete');
	await expect(items).toHaveCount(1);
	await page.keyboard.press(`${MOD}+z`);
	await expect(items).toHaveCount(2);

	// The singer, typed in place.
	await items.first().getByLabel('Quen canta').fill('Uxía');
	await items.first().getByLabel('Quen canta').press('Enter');
	await page.keyboard.press('Escape');
	await expect(items.first().getByLabel('Quen canta')).toHaveValue('Uxía');
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
		'[role="dialog"][aria-label="Buscar ordes"]'
	);
	expect(palette).toBeLessThan(100);
	await page.keyboard.type('procesamento');
	await page.keyboard.press('Enter');
	await expect(page).toHaveURL(/\/procesamento$/);

	const sheet = await responseTime(page, '?', '[role="dialog"][aria-label="Atallos de teclado"]');
	expect(sheet).toBeLessThan(100);
	await expect(page.getByRole('dialog').getByText('Reintentar os que fallaron')).toBeVisible();
	await page.keyboard.press('Escape');

	await page.keyboard.press('g');
	const navigation = await responseTime(page, 'b', 'input[aria-label^="Buscar por"]');
	expect(navigation).toBeLessThan(100);

	// Every main section passes axe's WCAG 2 A/AA rules.
	for (const path of [
		'/',
		'/engadir',
		'/procesamento',
		'/biblioteca',
		'/equipos',
		'/saidas',
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
