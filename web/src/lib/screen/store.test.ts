import { describe, expect, it } from 'vitest';
import { sha256Hex } from './sha256';
import { CorruptBlobError, MemoryStore, download } from './store';

const bytes = new Uint8Array(10_000).map((_, i) => (i * 7) & 0xff);
const sha = sha256Hex(bytes);

/** A server that serves `bytes`, honours Range and drops the line once, half-way. */
function flakyServer() {
	const asked: (string | null)[] = [];
	let dropped = false;
	const serve = async (_url: RequestInfo | URL, init?: RequestInit) => {
		const range = new Headers(init?.headers).get('Range');
		asked.push(range);
		const from = range ? Number(/bytes=(\d+)-/.exec(range)?.[1]) : 0;
		const body = bytes.slice(from);
		let pulls = 0;
		const stream = new ReadableStream<Uint8Array>({
			pull(controller) {
				pulls++;
				if (pulls === 1) controller.enqueue(body.slice(0, 4000));
				else if (!dropped) {
					dropped = true;
					controller.error(new Error('the Wi-Fi went away'));
				} else if (pulls === 2) controller.enqueue(body.slice(4000));
				else controller.close();
			}
		});
		return new Response(stream, { status: range ? 206 : 200 });
	};
	return { serve, asked };
}

describe('downloading a blob', () => {
	it('resumes where the connection dropped and checks the hash', async () => {
		const server = flakyServer();
		const seen: number[] = [];
		const blob = await download(sha, {
			fetch: server.serve,
			retryMs: 1,
			progress: (n) => seen.push(n)
		});
		expect(new Uint8Array(await blob.arrayBuffer())).toEqual(bytes);
		expect(server.asked).toEqual([null, 'bytes=4000-']);
		expect(seen.at(-1)).toBe(bytes.length);
	});

	it('refuses bytes that are not what the name says', async () => {
		const serve = (async () => new Response(bytes.slice(1))) as typeof fetch;
		await expect(download(sha, { fetch: serve })).rejects.toBeInstanceOf(CorruptBlobError);
	});

	it('gives up after the attempts it was given', async () => {
		const serve = (async () => new Response('', { status: 404 })) as typeof fetch;
		await expect(download(sha, { fetch: serve, attempts: 2, retryMs: 1 })).rejects.toThrow('404');
	});
});

describe('the memory store', () => {
	it('keeps only what it is told to keep', async () => {
		const store = new MemoryStore();
		await store.put('a', new Blob(['a']));
		await store.put('b', new Blob(['b']));
		await store.keep(new Set(['b']));
		expect(await store.has('a')).toBe(false);
		expect(await store.get('b')).not.toBeNull();
	});
});
