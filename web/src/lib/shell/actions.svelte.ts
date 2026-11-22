/**
 * What the operator does, as functions the commands, the buttons and the palette share. Every
 * change shows at once (optimistic) and is reverted with a notice if the server says no.
 *
 * Every screen (player) has its own queue, so "add" always has a target: the screen the operator
 * drives (chosen in the top strip), else the first one online.
 */
import type { Queue, QueueItem } from '#lib/contracts';
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

/** The screen the operator drives. */
export function player(): PlayerView | undefined {
	const players = live.state.players;
	return (
		players.find((p) => p.id === prefs.value.player) ?? players.find((p) => p.online) ?? players[0]
	);
}

export function choosePlayer(id: string): void {
	prefs.set('player', id);
}

export function nextPlayer(): void {
	const players = live.state.players;
	if (players.length < 2) return;
	const index = players.findIndex((p) => p.id === player()?.id);
	choosePlayer(players[(index + 1) % players.length].id);
}

export function queueOf(playerId: string | undefined): Queue | undefined {
	if (!playerId) return undefined;
	return (
		live.state.queues.find((q) => q.player_id === playerId) ?? {
			player_id: playerId,
			version: 0,
			items: []
		}
	);
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
	seek: (position: number) => order('seek', { position: Math.max(0, position) }),
	seekBy: (seconds: number) => {
		const target = player();
		if (!target) return;
		const at = positionNow(live.state, target, performance.now()) ?? 0;
		return order('seek', { position: Math.max(0, at + seconds) });
	},
	restart: () => {
		const target = player();
		const item = queueOf(target?.id)?.items.find((i) => i.id === target?.status.item_id);
		return order('seek', { position: item?.start ?? 0 });
	},
	volume: (value: number) => order('volume', { value: Math.round(value * 100) / 100 }),
	volumeBy: (step: number) => transport.volume((player()?.status.volume ?? 1) + step),
	pitch: (value: number) => order('pitch', { value }),
	pitchBy: (step: number) => order('pitch', { value: (player()?.status.semitones ?? 0) + step }),
	pitchReset: () => order('pitch', { value: 0 })
};

function setQueue(saved: Queue): void {
	live.state = {
		...live.state,
		queues: [...live.state.queues.filter((q) => q.player_id !== saved.player_id), saved]
	};
}

/**
 * Changes a queue's order or items: shown at once, saved with its version; on a conflict the
 * change is applied again to the newer queue. Undoable.
 */
export async function editQueue(
	label: string,
	change: (items: QueueItem[]) => QueueItem[],
	queue: Queue | undefined = queueOf(player()?.id)
): Promise<void> {
	if (!queue) return;
	const before = queue.items;
	const after = change(before);
	if (JSON.stringify(before) === JSON.stringify(after)) return;
	const revert = live.patch((state) => ({
		...state,
		queues: [
			...state.queues.filter((q) => q.player_id !== queue.player_id),
			{ ...queue, items: after }
		]
	}));
	const id = queue.player_id;
	const entry = {
		label,
		undo: async () => {
			await editQueue(label, () => before, queueOf(id)).then(() => void history.past.pop());
		},
		redo: async () => {
			const now = queueOf(id);
			if (now)
				await editQueue(label, () => change(now.items), now).then(() => void history.past.pop());
		}
	};
	history.push(entry);
	try {
		setQueue(await api.saveQueue({ ...queue, items: after }));
	} catch (error) {
		let problem: unknown = error;
		if (error instanceof ApiError && error.code === 'version_conflict' && error.body.current) {
			const current = error.body.current as Queue;
			try {
				setQueue(await api.saveQueue({ ...current, items: change(current.items) }));
				return;
			} catch (again) {
				problem = again;
			}
		}
		revert();
		history.past = history.past.filter((e) => e !== entry);
		fail(problem);
	}
}

/** Adds songs to the end of the screen's queue (or right after the song on air). */
export async function addToQueue(contentIds: string[], next = false): Promise<void> {
	const target = player();
	if (!target || !contentIds.length) return;
	const titles = contentIds.map((id) => content(id)?.title ?? id).join(', ');
	try {
		const saved = await api.addToQueue(
			target.id,
			contentIds.map((content_id) => ({ content_id }))
		);
		setQueue(saved);
		if (next) {
			const fresh = saved.items.slice(-contentIds.length).map((i) => i.id);
			await editQueue(
				i18n.t.cmd.addNext,
				(items) => {
					const moving = items.filter((i) => fresh.includes(i.id));
					const rest = items.filter((i) => !fresh.includes(i.id));
					const at = rest.findIndex((i) => i.id === target.status.item_id);
					return [...rest.slice(0, at + 1), ...moving, ...rest.slice(at + 1)];
				},
				saved
			);
		}
		toasts.show(i18n.t.library.added(titles, target.name));
	} catch (error) {
		fail(error);
	}
}

export function removeFromQueue(ids: string[]): Promise<void> {
	return editQueue(i18n.t.cmd.remove, (items) => items.filter((i) => !ids.includes(i.id)));
}

export function moveInQueue(ids: string[], step: -1 | 1): Promise<void> {
	return editQueue(step < 0 ? i18n.t.cmd.moveUp : i18n.t.cmd.moveDown, (list) => {
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

/** Puts `id` where `beforeId` is (or at the end): drag and drop. */
export function placeInQueue(id: string, beforeId: string | null): Promise<void> {
	return editQueue(i18n.t.live.dragHint, (items) => {
		const moving = items.find((i) => i.id === id);
		if (!moving || id === beforeId) return items;
		const rest = items.filter((i) => i.id !== id);
		const at = beforeId === null ? rest.length : rest.findIndex((i) => i.id === beforeId);
		return [...rest.slice(0, at), moving, ...rest.slice(at)];
	});
}

export function updateItem(id: string, change: Partial<QueueItem>): Promise<void> {
	return editQueue(i18n.t.live.singer, (items) =>
		items.map((i) => (i.id === id ? { ...i, ...change } : i))
	);
}

function setJob(id: string, job: Awaited<ReturnType<typeof api.jobAction>>): void {
	live.state = { ...live.state, jobs: live.state.jobs.map((j) => (j.id === id ? job : j)) };
}

export const jobs = {
	async act(ids: string[], action: 'cancel' | 'pause' | 'resume' | 'retry') {
		for (const id of ids) {
			try {
				setJob(id, await api.jobAction(id, action));
			} catch (error) {
				fail(error);
			}
		}
	},
	/** Retries on any worker but the one it failed on. */
	async retryElsewhere(id: string, failedOn: string | null) {
		const other = live.state.nodes.find(
			(n) => n.kind === 'worker' && n.online && n.id !== failedOn
		);
		try {
			// Retried first (its tasks go back to the queue), then pinned while nobody holds it.
			const retried = await api.jobAction(id, 'retry');
			setJob(id, other ? await api.changeJob(id, { pinned_node: other.id }) : retried);
		} catch (error) {
			fail(error);
		}
	},
	async priority(id: string, step: number) {
		const now = live.state.jobs.find((j) => j.id === id)?.tasks[0]?.priority ?? 0;
		try {
			setJob(id, await api.changeJob(id, { priority: now + step }));
		} catch (error) {
			fail(error);
		}
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
		toasts.show(i18n.t.library.trashed(ids.length));
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
	async exportMp4(ids: string[], aspect: '16:9' | '9:16' = '16:9') {
		for (const id of ids) {
			try {
				await api.exportVideo(id, aspect);
				toasts.show(i18n.t.library.exporting(content(id)?.title ?? id));
			} catch (error) {
				fail(error);
			}
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
