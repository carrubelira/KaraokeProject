/** The v4 server's HTTP API, with the operator's session cookie. */
import type { Lyrics, Manifest, PlayerCommand, PlayerConfig, Queue } from '#lib/contracts';
import type { Content, Job, LyricsCandidate, Session } from './types';

export class ApiError extends Error {
	constructor(
		readonly status: number,
		readonly code: string,
		message: string,
		readonly body: Record<string, unknown> = {}
	) {
		super(message);
	}
}

async function call<T>(
	method: string,
	path: string,
	body?: unknown,
	init: RequestInit = {}
): Promise<T> {
	const headers = new Headers(init.headers);
	if (body !== undefined && !(body instanceof Blob) && !(body instanceof ArrayBuffer)) {
		headers.set('Content-Type', 'application/json');
	}
	const response = await fetch(path, {
		...init,
		method,
		headers,
		credentials: 'same-origin',
		body:
			body === undefined
				? undefined
				: body instanceof Blob || body instanceof ArrayBuffer
					? (body as BodyInit)
					: JSON.stringify(body)
	});
	if (!response.ok) {
		let data: Record<string, unknown> = {};
		try {
			data = (await response.json()) as Record<string, unknown>;
		} catch {
			// A proxy's HTML page: the status says enough.
		}
		throw new ApiError(
			response.status,
			typeof data.code === 'string' ? data.code : 'http_error',
			typeof data.detail === 'string' ? data.detail : response.statusText,
			data
		);
	}
	if (response.status === 204 || method === 'HEAD') return undefined as T;
	if (response.headers.get('Content-Type')?.startsWith('text/plain')) {
		return (await response.text()) as T;
	}
	return (await response.json()) as T;
}

const song = (id: string) => `/api/contents/${encodeURIComponent(id)}`;

export interface NewJob {
	url?: string;
	upload?: string;
	title?: string;
	artist?: string;
	language?: string;
	lyrics?: string;
	auto_confirm?: boolean;
}

export interface Confirmation {
	title: string;
	artist: string | null;
	language: string;
	lyrics: string | null;
	/** A screen whose queue gets the song once it is made. */
	queue_on?: string | null;
}

export const api = {
	signIn: (token: string) => call<Session>('POST', '/api/session', { token }),
	session: () => call<Session>('GET', '/api/session'),
	signOut: () => call<void>('DELETE', '/api/session'),
	savePreferences: (preferences: Record<string, unknown>) =>
		call<Record<string, unknown>>('PUT', '/api/session/preferences', preferences),

	manifest: (id: string) => call<Manifest>('GET', `${song(id)}/manifest`),
	lyrics: (id: string) => call<Lyrics>('GET', `${song(id)}/lyrics`),
	saveLyrics: (id: string, base: string, lyrics: Lyrics) =>
		call<Content>('PUT', `${song(id)}/lyrics`, { base, lyrics }),
	trash: (id: string) => call<void>('DELETE', song(id)),
	restore: (id: string) => call<Content>('POST', `${song(id)}/restore`),
	blobUrl: (sha: string) => `/api/blobs/${sha}`,

	createJob: (body: NewJob) => call<Job>('POST', '/api/jobs', body),
	exportVideo: (contentId: string, aspect: '16:9' | '9:16') =>
		call<Job>('POST', '/api/jobs', { kind: 'render', content_id: contentId, aspect }),
	jobAction: (id: string, action: 'cancel' | 'pause' | 'resume' | 'retry') =>
		call<Job>('POST', `/api/jobs/${id}/${action}`),
	confirm: (id: string, choice: Confirmation) =>
		call<Job>('POST', `/api/jobs/${id}/confirm`, choice),
	changeJob: (id: string, change: { priority?: number; pinned_node?: string; unpin?: boolean }) =>
		call<Job>('PATCH', `/api/jobs/${id}`, change),
	taskLog: (jobId: string, key: string) =>
		call<string>('GET', `/api/jobs/${jobId}/tasks/${encodeURIComponent(key)}/log`),

	searchLyrics: (q: string, duration?: number | null) =>
		call<LyricsCandidate[]>(
			'GET',
			`/api/lyrics/search?q=${encodeURIComponent(q)}${duration ? `&duration=${Math.round(duration)}` : ''}`
		),

	enrollment: (kind: 'worker' | 'player') =>
		call<{ token: string; kind: string; expires_in_hours: number }>('POST', '/api/enrollments', {
			kind
		}),
	revoke: (id: string) => call<void>('DELETE', `/api/nodes/${id}`),
	server: () =>
		call<{ version: string; fingerprint: string; now: number; tls: boolean }>('GET', '/api/server'),

	setConfig: (id: string, config: PlayerConfig) =>
		call<PlayerConfig>('PUT', `/api/players/${id}/config`, config),
	command: (
		id: string,
		order: { command: string; item_id?: string; position?: number; value?: number }
	) => call<PlayerCommand>('POST', `/api/players/${id}/commands`, order),
	saveQueue: (queue: Queue) => call<Queue>('PUT', `/api/players/${queue.player_id}/queue`, queue),
	addToQueue: (
		playerId: string,
		items: { content_id: string; singer?: string | null }[],
		first = false
	) => call<Queue>('POST', `/api/players/${playerId}/queue/items`, { items, first }),

	createUpload: (filename: string, size: number) =>
		call<{ id: string; offset: number; size: number; blob: string | null }>(
			'POST',
			'/api/uploads',
			{ filename, size }
		),
	uploadState: (id: string) =>
		call<{ id: string; offset: number; size: number; blob: string | null }>(
			'GET',
			`/api/uploads/${id}`
		),
	appendUpload: (id: string, offset: number, chunk: Blob) =>
		call<{ id: string; offset: number; size: number; blob: string | null }>(
			'PATCH',
			`/api/uploads/${id}`,
			chunk,
			{ headers: { 'Upload-Offset': String(offset) } }
		)
};
