/**
 * What a screen keeps of the songs (decision 011): their blobs, by SHA-256, in IndexedDB, so a
 * reload or tomorrow's party finds them here. Over plain HTTP there is no Cache API nor OPFS;
 * IndexedDB works everywhere, and where it does not (a private window) the blobs stay in memory.
 *
 * A blob is downloaded from the stage (`/api/screens/blobs/…`, with `Range`, so a dropped
 * connection carries on where it stopped), hashed while it arrives and kept only if it is what
 * its name says. The work runs in a Worker (`fetcher.worker.ts`): hashing a video never holds up
 * the frame loop.
 */
import { Sha256 } from './sha256';

export interface BlobStore {
	has(sha: string): Promise<boolean>;
	get(sha: string): Promise<Blob | null>;
	put(sha: string, blob: Blob): Promise<void>;
	/** Deletes every blob not in `keep`. */
	keep(keep: ReadonlySet<string>): Promise<void>;
}

const DB = 'karaoke-screen';
const BLOBS = 'blobs';

function request<T>(req: IDBRequest<T>): Promise<T> {
	return new Promise((resolve, reject) => {
		req.onsuccess = () => resolve(req.result);
		req.onerror = () => reject(req.error ?? new Error('IndexedDB failed'));
	});
}

class IndexedStore implements BlobStore {
	constructor(private readonly db: IDBDatabase) {}

	#store(mode: IDBTransactionMode): IDBObjectStore {
		return this.db.transaction(BLOBS, mode).objectStore(BLOBS);
	}

	async has(sha: string): Promise<boolean> {
		return (await request(this.#store('readonly').count(sha))) > 0;
	}

	async get(sha: string): Promise<Blob | null> {
		const found: unknown = await request(this.#store('readonly').get(sha));
		return found instanceof Blob ? found : null;
	}

	async put(sha: string, blob: Blob): Promise<void> {
		await request(this.#store('readwrite').put(blob, sha));
	}

	async keep(keep: ReadonlySet<string>): Promise<void> {
		const keys = await request(this.#store('readonly').getAllKeys());
		const store = this.#store('readwrite');
		await Promise.all(
			keys
				.filter((k): k is string => typeof k === 'string' && !keep.has(k))
				.map((k) => request(store.delete(k)))
		);
	}
}

export class MemoryStore implements BlobStore {
	readonly #blobs = new Map<string, Blob>();
	async has(sha: string) {
		return this.#blobs.has(sha);
	}
	async get(sha: string) {
		return this.#blobs.get(sha) ?? null;
	}
	async put(sha: string, blob: Blob) {
		this.#blobs.set(sha, blob);
	}
	async keep(keep: ReadonlySet<string>) {
		for (const sha of [...this.#blobs.keys()]) if (!keep.has(sha)) this.#blobs.delete(sha);
	}
}

/** IndexedDB if this browser lets the page keep it, else memory. */
export async function openStore(): Promise<BlobStore> {
	try {
		const open = indexedDB.open(DB, 1);
		open.onupgradeneeded = () => open.result.createObjectStore(BLOBS);
		return new IndexedStore(await request(open));
	} catch {
		return new MemoryStore();
	}
}

export const blobUrl = (sha: string): string => `/api/screens/blobs/${sha}`;

export class CorruptBlobError extends Error {}

export interface DownloadOptions {
	fetch?: typeof fetch;
	/** Bytes received so far, as they arrive. */
	progress?: (received: number) => void;
	signal?: AbortSignal;
	attempts?: number;
	/** ms before trying again; doubles every time. */
	retryMs?: number;
}

/**
 * Downloads one blob, resuming after a dropped connection, and checks its hash. Returns its
 * bytes as a Blob; throws `CorruptBlobError` if they are not what the name says.
 */
export async function download(sha: string, options: DownloadOptions = {}): Promise<Blob> {
	const get = options.fetch ?? fetch;
	const attempts = options.attempts ?? 6;
	let wait = options.retryMs ?? 500;
	let chunks: Uint8Array[] = [];
	let hasher = new Sha256();
	let received = 0;
	for (let attempt = 1; ; attempt++) {
		try {
			const headers: HeadersInit = received ? { Range: `bytes=${received}-` } : {};
			const answer = await get(blobUrl(sha), { headers, signal: options.signal });
			if (answer.status === 200 && received) {
				// The server sent it all again: start over.
				chunks = [];
				hasher = new Sha256();
				received = 0;
			} else if (!answer.ok) {
				throw new Error(`HTTP ${answer.status}`);
			}
			const reader = answer.body?.getReader();
			if (!reader) throw new Error('no body');
			for (;;) {
				const { done, value } = await reader.read();
				if (done) break;
				chunks.push(value);
				hasher.update(value);
				received += value.length;
				options.progress?.(received);
			}
			break;
		} catch (error) {
			if (options.signal?.aborted || attempt >= attempts) throw error;
			await new Promise((resolve) => setTimeout(resolve, wait));
			wait = Math.min(wait * 2, 10_000);
		}
	}
	const seen = hasher.hex();
	if (seen !== sha) throw new CorruptBlobError(`${sha} arrived as ${seen}`);
	return new Blob(chunks as BlobPart[]);
}
