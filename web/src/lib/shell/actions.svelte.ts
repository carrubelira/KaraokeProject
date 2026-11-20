/**
 * What the operator does, as functions the commands, the buttons and the palette share. Every
 * change shows at once (optimistic) and is reverted with a notice if the server says no;
 * playlist edits that meet a newer version are applied again on top of it.
 */
import { SvelteMap } from 'svelte/reactivity';
import type { Playlist, PlaylistItem } from '#lib/contracts';
import { api, ApiError } from '#lib/control/api.js';
import { live } from '#lib/control/live.svelte.js';
import { positionNow } from '#lib/control/state.js';
import { toasts } from '#lib/control/toasts.svelte.js';
import type { Content, PlayerView } from '#lib/control/types.js';
import { history } from '#lib/commands/undo.svelte.js';
import { i18n } from '#lib/i18n';
import { prefs } from './prefs.svelte';

export function fail(error: unknown): void {
	const text = error instanceof Error ? error.message : String(error);
	toasts.show(i18n.t.app.failed(text), 'error');
}

export function player(): PlayerView | undefined {
	const players = live.state.players;
	return (
		players.find((p) => p.id === prefs.value.player) ?? players.find((p) => p.online) ?? players[0]
	);
}

export function playlist(): Playlist | undefined {
	const id = player()?.config.playlist_id ?? prefs.value.playlist;
	return live.state.playlists.find((p) => p.id === id);
}

export function content(id: string): Content | undefined {
	return live.state.contents.find((c) => c.id === id);
}

async function order(
	command: string,
	extra: { item_id?: string; position?: number; value?: number } = {}
) {
	const target = player();
	if (!target) return;
	try {
		await api.command(target.id, { command, ...extra });
	} catch (error) {
		fail(error);
	}
}

export const transport = {
	toggle: () => order(player()?.status.state === 'playing' ? 'pause' : 'play'),
	play: () => order('play'),
	pause: () => order('pause'),
	next: () => order('next'),
	previous: () => order('previous'),
	stop: () => order('stop'),
	cue: (itemId: string) => order('load', { item_id: itemId }),
	playItem: (itemId: string) => order('play', { item_id: itemId }),
	seekBy: (seconds: number) => {
		const target = player();
		if (!target) return;
		const at = positionNow(live.state, target, performance.now()) ?? 0;
		return order('seek', { position: Math.max(0, at + seconds) });
	},
	restart: () => {
		const target = player();
		const item = playlist()?.items.find((i) => i.id === target?.status.item_id);
		return order('seek', { position: item?.start ?? 0 });
	},
	volumeBy: (step: number) =>
		order('volume', { value: Math.round(((player()?.status.volume ?? 1) + step) * 100) / 100 }),
	pitchBy: (step: number) => order('pitch', { value: (player()?.status.semitones ?? 0) + step }),
	pitchReset: () => order('pitch', { value: 0 })
};

let counter = 0;
export function itemId(): string {
	counter += 1;
	return `i${Date.now().toString(36)}${counter.toString(36)}`;
}

function same(a: PlaylistItem[], b: PlaylistItem[]): boolean {
	return JSON.stringify(a) === JSON.stringify(b);
}

function save(list: Playlist, items: PlaylistItem[]): Promise<Playlist> {
	return api.savePlaylist({ ...list, items });
}

/**
 * Changes a playlist's items: shown at once, saved with its version; on a conflict the change is
 * applied again to the newer list. Undoable.
 */
export async function editPlaylist(
	label: string,
	change: (items: PlaylistItem[]) => PlaylistItem[],
	list: Playlist | undefined = playlist()
): Promise<void> {
	if (!list) return;
	const before = list.items;
	const after = change(before);
	if (same(before, after)) return;
	const revert = live.patch((state) => ({
		...state,
		playlists: state.playlists.map((p) => (p.id === list.id ? { ...p, items: after } : p))
	}));
	// On the undo stack at once: the next key may be Mod+Z before the server has answered.
	const id = list.id;
	const entry = {
		label,
		undo: async () => {
			const now = live.state.playlists.find((p) => p.id === id);
			if (now) await editPlaylist(label, () => before, now).then(() => void history.past.pop());
		},
		redo: async () => {
			const now = live.state.playlists.find((p) => p.id === id);
			if (now)
				await editPlaylist(label, () => change(now.items), now).then(() => void history.past.pop());
		}
	};
	history.push(entry);
	const withdraw = () => {
		history.past = history.past.filter((e) => e !== entry);
	};
	let saved: Playlist;
	try {
		saved = await save(list, after);
	} catch (error) {
		if (error instanceof ApiError && error.code === 'version_conflict' && error.body.current) {
			const current = error.body.current as Playlist;
			try {
				saved = await save(current, change(current.items));
			} catch (again) {
				revert();
				withdraw();
				return fail(again);
			}
		} else {
			revert();
			withdraw();
			return fail(error);
		}
	}
	live.state = {
		...live.state,
		playlists: live.state.playlists.map((p) => (p.id === saved.id ? saved : p))
	};
}

export function addToPlaylist(contentIds: string[], next = false): Promise<void> {
	const current = player()?.status.item_id;
	const items = contentIds.map((content_id) => ({
		id: itemId(),
		content_id,
		manifest: null,
		start: null,
		end: null,
		semitones: 0,
		singer: null
	}));
	const titles = contentIds.map((id) => content(id)?.title ?? id).join(', ');
	return editPlaylist(i18n.t.library.added(titles), (list) => {
		if (!next) return [...list, ...items];
		const at = list.findIndex((i) => i.id === current);
		return [...list.slice(0, at + 1), ...items, ...list.slice(at + 1)];
	}).then(() => toasts.show(i18n.t.library.added(titles)));
}

export function removeFromPlaylist(ids: string[]): Promise<void> {
	return editPlaylist(i18n.t.cmd.remove, (list) => list.filter((i) => !ids.includes(i.id)));
}

export function moveInPlaylist(ids: string[], step: -1 | 1): Promise<void> {
	return editPlaylist(step < 0 ? i18n.t.cmd.moveUp : i18n.t.cmd.moveDown, (list) => {
		const items = list.slice();
		const order = step < 0 ? items.map((_, i) => i) : items.map((_, i) => items.length - 1 - i);
		for (const index of order) {
			const target = index + step;
			if (
				ids.includes(items[index].id) &&
				target >= 0 &&
				target < items.length &&
				!ids.includes(items[target].id)
			) {
				[items[index], items[target]] = [items[target], items[index]];
			}
		}
		return items;
	});
}

export function updateItem(id: string, change: Partial<PlaylistItem>): Promise<void> {
	return editPlaylist(i18n.t.live.playlist, (list) =>
		list.map((i) => (i.id === id ? { ...i, ...change } : i))
	);
}

export const jobs = {
	async act(ids: string[], action: 'cancel' | 'pause' | 'resume' | 'retry') {
		for (const id of ids) {
			try {
				const job = await api.jobAction(id, action);
				live.state = { ...live.state, jobs: live.state.jobs.map((j) => (j.id === id ? job : j)) };
			} catch (error) {
				fail(error);
			}
		}
		if (action === 'pause' || action === 'resume') {
			const inverse = action === 'pause' ? 'resume' : 'pause';
			history.push({
				label: action === 'pause' ? i18n.t.cmd.pauseJob : i18n.t.cmd.resumeJob,
				undo: () => jobs.act(ids, inverse).then(() => void history.past.pop()),
				redo: () => jobs.act(ids, action).then(() => void history.past.pop())
			});
		}
	},
	async priority(ids: string[], step: number) {
		const before = new SvelteMap(
			ids.map((id) => [id, live.state.jobs.find((j) => j.id === id)?.tasks[0]?.priority ?? 0])
		);
		for (const id of ids) {
			try {
				const job = await api.changeJob(id, { priority: (before.get(id) ?? 0) + step });
				live.state = { ...live.state, jobs: live.state.jobs.map((j) => (j.id === id ? job : j)) };
			} catch (error) {
				fail(error);
			}
		}
		history.push({
			label: step > 0 ? i18n.t.cmd.prioritise : i18n.t.cmd.deprioritise,
			undo: async () => {
				for (const [id, p] of before) await api.changeJob(id, { priority: p }).catch(fail);
			},
			redo: async () => {
				for (const [id, p] of before) await api.changeJob(id, { priority: p + step }).catch(fail);
			}
		});
	},
	retryFailed: () =>
		jobs.act(
			live.state.jobs.filter((j) => j.state === 'failed').map((j) => j.id),
			'retry'
		)
};

export const library = {
	async trash(ids: string[]) {
		for (const id of ids) await api.trash(id).catch(fail);
		live.state = {
			...live.state,
			contents: live.state.contents.filter((c) => !ids.includes(c.id))
		};
		history.push({
			label: i18n.t.cmd.trash,
			undo: async () => {
				for (const id of ids) await api.restore(id).catch(fail);
			},
			redo: async () => {
				for (const id of ids) await api.trash(id).catch(fail);
			}
		});
	},
	async exportMp4(ids: string[]) {
		for (const id of ids) {
			await api.createJob({ kind: 'render', content_id: id }).catch(fail);
		}
	}
};

export async function undo(): Promise<void> {
	try {
		const action = await history.undo();
		toasts.show(action ? i18n.t.app.undone(action.label) : i18n.t.app.nothingToUndo);
	} catch (error) {
		fail(error);
	}
}

export async function redo(): Promise<void> {
	try {
		const action = await history.redo();
		if (action) toasts.show(i18n.t.app.redone(action.label));
	} catch (error) {
		fail(error);
	}
}
