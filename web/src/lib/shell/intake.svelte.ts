/**
 * New karaokes from anywhere: a file dropped on any screen, a link pasted, or the Create form.
 * Files upload (resumably) and become jobs; links become jobs at once.
 */
import { api } from '#lib/control/api.js';
import { live } from '#lib/control/live.svelte.js';
import { toasts } from '#lib/control/toasts.svelte.js';
import { Upload } from '#lib/control/upload.svelte.js';
import { i18n } from '#lib/i18n';
import { fail } from './actions.svelte';

export interface Options {
	lyrics?: string;
	lrclib?: boolean;
	language?: string;
	title?: string;
	artist?: string;
}

const MEDIA = /\.(mp3|m4a|aac|wav|flac|ogg|opus|mp4|mkv|webm|mov)$/i;

class Intake {
	uploads = $state<Upload[]>([]);
	language = $state('gl');

	isMedia(file: File): boolean {
		return (
			MEDIA.test(file.name) || file.type.startsWith('audio/') || file.type.startsWith('video/')
		);
	}

	async file(file: File, options: Options = {}): Promise<void> {
		const upload = new Upload(file);
		this.uploads = [...this.uploads, upload];
		try {
			await upload.run();
			const job = await api.createJob({
				upload: upload.id,
				language: options.language ?? this.language,
				lyrics: options.lyrics || null,
				lrclib: options.lrclib ?? false,
				title: options.title || null,
				artist: options.artist || null
			});
			live.state = {
				...live.state,
				jobs: [job, ...live.state.jobs.filter((j) => j.id !== job.id)]
			};
			toasts.show(i18n.t.create.queued(job.title));
		} catch (error) {
			fail(error);
		} finally {
			this.uploads = this.uploads.filter((u) => u !== upload);
		}
	}

	async files(files: Iterable<File>, options: Options = {}): Promise<void> {
		await Promise.all([...files].filter((f) => this.isMedia(f)).map((f) => this.file(f, options)));
	}

	async link(url: string, options: Options = {}): Promise<void> {
		try {
			const job = await api.createJob({
				url,
				language: options.language ?? this.language,
				lyrics: options.lyrics || null,
				lrclib: options.lrclib ?? true,
				title: options.title || null,
				artist: options.artist || null
			});
			live.state = {
				...live.state,
				jobs: [job, ...live.state.jobs.filter((j) => j.id !== job.id)]
			};
			toasts.show(i18n.t.create.queued(job.title));
		} catch (error) {
			fail(error);
		}
	}
}

export const intake = new Intake();

export function looksLikeLink(text: string): boolean {
	return /^https?:\/\/\S+$/.test(text.trim());
}
