/** The v4 server's HTTP API, with the operator's session cookie. */
import type { Lyrics, Manifest, PlayerCommand, PlayerConfig, Playlist } from '#lib/contracts';
import type { Candidate, Content, Job, NodeView, PlayerView, Session } from './types';

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
	return (await response.json()) as T;
}

export const api = {
	signIn: (token: string) => call<Session>('POST', '/api/session', { token }),
	session: () => call<Session>('GET', '/api/session'),
	signOut: () => call<void>('DELETE', '/api/session'),
	savePreferences: (preferences: Record<string, unknown>) =>
		call<Record<string, unknown>>('PUT', '/api/session/preferences', preferences),

	contents: (trash = false) => call<Content[]>('GET', `/api/contents${trash ? '?trash=true' : ''}`),
	manifest: (id: string) =>
		call<Manifest>('GET', `/api/contents/${encodeURIComponent(id)}/manifest`),
	lyrics: (id: string) => call<Lyrics>('GET', `/api/contents/${encodeURIComponent(id)}/lyrics`),
	saveLyrics: (id: string, base: string, lyrics: Lyrics) =>
		call<Content>('PUT', `/api/contents/${encodeURIComponent(id)}/lyrics`, { base, lyrics }),
	trash: (id: string) => call<void>('DELETE', `/api/contents/${encodeURIComponent(id)}`),
	restore: (id: string) => call<Content>('POST', `/api/contents/${encodeURIComponent(id)}/restore`),
	blobUrl: (sha: string) => `/api/blobs/${sha}`,

	jobs: () => call<Job[]>('GET', '/api/jobs'),
	createJob: (body: Record<string, unknown>) => call<Job>('POST', '/api/jobs', body),
	jobAction: (id: string, action: 'cancel' | 'pause' | 'resume' | 'retry') =>
		call<Job>('POST', `/api/jobs/${id}/${action}`),
	changeJob: (id: string, change: { priority?: number; pinned_node?: string; unpin?: boolean }) =>
		call<Job>('PATCH', `/api/jobs/${id}`, change),

	nodes: () => call<NodeView[]>('GET', '/api/nodes'),
	enrollment: (kind: 'worker' | 'player') =>
		call<{ token: string; kind: string; expires_in_hours: number }>('POST', '/api/enrollments', {
			kind
		}),
	revoke: (id: string) => call<void>('DELETE', `/api/nodes/${id}`),
	server: () =>
		call<{ version: string; fingerprint: string; now: number; tls: boolean }>('GET', '/api/server'),

	playlists: () => call<Playlist[]>('GET', '/api/playlists'),
	createPlaylist: (name: string, player_id?: string) =>
		call<Playlist>('POST', '/api/playlists', { name, player_id }),
	savePlaylist: (playlist: Playlist) =>
		call<Playlist>('PUT', `/api/playlists/${playlist.id}`, playlist),
	deletePlaylist: (id: string) => call<void>('DELETE', `/api/playlists/${id}`),

	players: () => call<PlayerView[]>('GET', '/api/players'),
	setConfig: (id: string, config: PlayerConfig) =>
		call<PlayerConfig>('PUT', `/api/players/${id}/config`, config),
	command: (
		id: string,
		order: { command: string; item_id?: string; position?: number; value?: number }
	) => call<PlayerCommand>('POST', `/api/players/${id}/commands`, order),

	searchLyrics: (q: string, duration?: number) =>
		call<Candidate[]>(
			'GET',
			`/api/lyrics/search?q=${encodeURIComponent(q)}${duration ? `&duration=${duration}` : ''}`
		),

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
			{
				headers: { 'Upload-Offset': String(offset) }
			}
		)
};
