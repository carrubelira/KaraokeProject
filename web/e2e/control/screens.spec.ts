/**
 * Two web screens on one stage (decision 011), against the real server (no sound: `--audio
 * off`, the stage keeps time alone): both download the song and stop on its first frame, the
 * operator is told who is ready, nothing plays until the start, and then both play.
 */
import { expect, test, type APIRequestContext } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const SERVER = 'http://127.0.0.1:8799';
const token = () =>
	readFileSync(fileURLToPath(new URL('./.token', import.meta.url)), 'utf-8').trim();

interface StageView {
	session: { state: string; epoch: number };
	screens: {
		id: string;
		online: boolean;
		counts: boolean;
		status: { state: string; ready: boolean; epoch: number | null } | null;
	}[];
}

function client(request: APIRequestContext) {
	const headers = { Authorization: `Bearer ${token()}` };
	const call = async <T>(method: string, path: string, data?: unknown): Promise<T> => {
		const answer = await request.fetch(`${SERVER}${path}`, { method, headers, data });
		expect(answer.ok(), `${method} ${path}: ${await answer.text()}`).toBe(true);
		return (await answer.json()) as T;
	};
	return {
		call,
		stage: () => call<StageView>('GET', '/api/stage'),
		order: (command: string, extra: Record<string, unknown> = {}) =>
			call<{ state: string; epoch: number }>('POST', '/api/stage/commands', { command, ...extra })
	};
}

test('two screens get ready, wait for the operator and play together', async ({
	browser,
	request
}) => {
	test.setTimeout(120_000);
	const api = client(request);

	// A song, made by the fake worker and put in the queue.
	const bytes = Buffer.concat([Buffer.from('ID3'), Buffer.alloc(2000)]);
	const upload = await api.call<{ id: string }>('POST', '/api/uploads', {
		filename: 'Pantallas.mp3',
		size: bytes.length
	});
	const patched = await request.fetch(`${SERVER}/api/uploads/${upload.id}`, {
		method: 'PATCH',
		headers: { Authorization: `Bearer ${token()}`, 'Upload-Offset': '0' },
		data: bytes
	});
	expect(patched.ok()).toBe(true);
	const job = await api.call<{ id: string }>('POST', '/api/jobs', {
		upload: upload.id,
		title: 'Pantallas',
		lyrics: 'la la la'
	});
	await expect
		.poll(async () => (await api.call<{ state: string }>('GET', `/api/jobs/${job.id}`)).state, {
			timeout: 60_000
		})
		.toBe('review');
	await api.call('POST', `/api/jobs/${job.id}/confirm`, {
		title: 'Pantallas',
		language: 'gl',
		lyrics: 'la la la',
		add_to_queue: true
	});
	await expect
		.poll(async () => (await api.call<{ state: string }>('GET', `/api/jobs/${job.id}`)).state, {
			timeout: 60_000
		})
		.toBe('done');

	// Two screens, as two browsers on the LAN would open them.
	const [tv, laptop] = await Promise.all([browser.newPage(), browser.newPage()]);
	await tv.goto('/pantalla?screen=e2e-tv&kiosk');
	await laptop.goto('/pantalla?screen=e2e-laptop&kiosk');
	await expect
		.poll(async () => (await api.stage()).screens.filter((s) => s.online).length)
		.toBeGreaterThanOrEqual(2);

	// Cued: both download it and stop on its first frame; the operator sees them ready.
	const cued = await api.order('cue');
	const ready = async () => {
		const stage = await api.stage();
		const ours = stage.screens.filter((s) => s.id.startsWith('e2e-') && s.online);
		return (
			stage.session.state === 'cued' &&
			ours.length === 2 &&
			ours.every((s) => s.status?.ready && s.status.epoch === cued.epoch)
		);
	};
	await expect.poll(ready, { timeout: 30_000 }).toBe(true);
	await expect(tv.getByText('Lista para comezar')).toBeVisible();
	await expect(laptop.getByText('Lista para comezar')).toBeVisible();

	// Nothing plays until the operator starts it.
	await tv.waitForTimeout(1000);
	expect((await api.stage()).session.state).toBe('cued');

	const started = await api.order('start');
	expect(started.state).toBe('playing');
	const states = async () =>
		(await api.stage()).screens
			.filter((s) => s.id.startsWith('e2e-'))
			.map((s) => s.status?.state)
			.sort();
	await expect.poll(states, { timeout: 10_000 }).toEqual(['playing', 'playing']);

	// A pause stops both on the same position.
	await api.order('pause');
	await expect.poll(states, { timeout: 10_000 }).toEqual(['paused', 'paused']);
	await api.order('stop');
});
