/// <reference lib="webworker" />
/**
 * Downloads and checks a screen's blobs off the main thread (see `store.ts`), and keeps them in
 * the screen's IndexedDB, which the page then reads.
 */
import { download, openStore, type BlobStore } from './store';

export type FetchRequest = { id: number; sha: string };
export type FetchReply =
	| { id: number; kind: 'progress'; received: number }
	| { id: number; kind: 'done'; inMemory: Blob | null }
	| { id: number; kind: 'failed'; error: string };

const scope = self as unknown as DedicatedWorkerGlobalScope;
let store: Promise<BlobStore> | null = null;

scope.onmessage = async (message: MessageEvent<FetchRequest>) => {
	const { id, sha } = message.data;
	store ??= openStore();
	try {
		const kept = await store;
		if (!(await kept.has(sha))) {
			let last = 0;
			const blob = await download(sha, {
				progress: (received) => {
					if (received - last > 256 * 1024) {
						last = received;
						scope.postMessage({ id, kind: 'progress', received } satisfies FetchReply);
					}
				}
			});
			try {
				await kept.put(sha, blob);
			} catch {
				// No room (or no IndexedDB): the page keeps this one in memory.
				scope.postMessage({ id, kind: 'done', inMemory: blob } satisfies FetchReply);
				return;
			}
		}
		scope.postMessage({ id, kind: 'done', inMemory: null } satisfies FetchReply);
	} catch (error) {
		scope.postMessage({ id, kind: 'failed', error: String(error) } satisfies FetchReply);
	}
};
