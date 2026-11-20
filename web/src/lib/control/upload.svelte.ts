/**
 * Resumable uploads (plan v4 §7): the file goes up in 8 MiB pieces; a piece that fails is sent
 * again from the offset the server has, so a flaky Wi-Fi costs a retry, not the whole file.
 */
import { api, ApiError } from './api';

const CHUNK = 8 * 1024 * 1024;
const RETRIES = 5;

export class Upload {
	id = $state<string | null>(null);
	sent = $state(0);
	blob = $state<string | null>(null);
	error = $state<string | null>(null);
	cancelled = false;

	constructor(
		readonly file: File,
		private readonly client = api,
		private readonly wait = (ms: number) => new Promise((r) => setTimeout(r, ms))
	) {}

	get fraction(): number {
		return this.file.size ? this.sent / this.file.size : 0;
	}

	/** Uploads to the end; resolves with the blob hash. */
	async run(): Promise<string> {
		const created = await this.client.createUpload(this.file.name, this.file.size);
		this.id = created.id;
		let offset = 0;
		let failures = 0;
		while (offset < this.file.size) {
			if (this.cancelled) throw new Error('cancelled');
			const chunk = this.file.slice(offset, offset + CHUNK);
			try {
				const state = await this.client.appendUpload(created.id, offset, chunk);
				offset = state.offset;
				this.sent = offset;
				if (state.blob) {
					this.blob = state.blob;
					return state.blob;
				}
				failures = 0;
			} catch (error) {
				if (error instanceof ApiError && error.code === 'bad_offset') {
					offset = Number(error.body.offset ?? offset);
					continue;
				}
				if (error instanceof ApiError && error.status < 500 && error.status !== 408) {
					this.error = error.message;
					throw error;
				}
				failures += 1;
				if (failures > RETRIES) {
					this.error = error instanceof Error ? error.message : String(error);
					throw error;
				}
				await this.wait(500 * 2 ** failures);
				offset = (await this.client.uploadState(created.id)).offset;
			}
		}
		const done = await this.client.uploadState(created.id);
		if (!done.blob) throw new Error('the upload did not finish');
		this.blob = done.blob;
		return done.blob;
	}
}
