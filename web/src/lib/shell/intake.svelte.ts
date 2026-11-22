/**
 * New songs from anywhere: a link pasted (on any screen or in Add) or a file dropped. Nothing is
 * asked first: the job starts with its analysis (which song is it? its lyrics?) and waits for
 * the operator's review in Add before the heavy work.
 */
import { api } from '#lib/control/api.js';
import { live } from '#lib/control/live.svelte.js';
import type { Job } from '#lib/control/types.js';
import { Upload } from '#lib/control/upload.svelte.js';
import { fail } from './actions.svelte';
import { prefs } from './prefs.svelte';

const MEDIA = /\.(mp3|m4a|aac|wav|flac|ogg|opus|mp4|mkv|webm|mov)$/i;

function shown(job: Job): Job {
	live.state = { ...live.state, jobs: [job, ...live.state.jobs.filter((j) => j.id !== job.id)] };
	return job;
}

class Intake {
	uploads = $state<Upload[]>([]);

	isMedia(file: File): boolean {
		return (
			MEDIA.test(file.name) || file.type.startsWith('audio/') || file.type.startsWith('video/')
		);
	}

	async file(file: File): Promise<Job | null> {
		const upload = new Upload(file);
		this.uploads = [...this.uploads, upload];
		try {
			await upload.run();
			return shown(
				await api.createJob({
					upload: upload.id ?? undefined,
					auto_confirm: prefs.value.autoConfirm
				})
			);
		} catch (error) {
			fail(error);
			return null;
		} finally {
			this.uploads = this.uploads.filter((u) => u !== upload);
		}
	}

	async files(files: Iterable<File>): Promise<void> {
		await Promise.all([...files].filter((f) => this.isMedia(f)).map((f) => this.file(f)));
	}

	async link(url: string): Promise<Job | null> {
		try {
			return shown(await api.createJob({ url, auto_confirm: prefs.value.autoConfirm }));
		} catch (error) {
			fail(error);
			return null;
		}
	}
}

export const intake = new Intake();

export function looksLikeLink(text: string): boolean {
	return /^https?:\/\/\S+$/.test(text.trim());
}
