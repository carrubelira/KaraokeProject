/**
 * What the operator does, as functions the commands, the buttons and the palette share. Every
 * change shows at once (optimistic) and is reverted with a notice if the server says no.
 *
 * There is one stage per backend (decision 011): one queue, one session. Nothing plays until the
 * operator says so: a song is cued (the audio and the screens get it ready) and then started;
 * if a screen is not ready yet, starting asks first, and that screen joins in step.
 */
import type { Queue, QueueItem, Session } from '#lib/contracts';
import { screenName } from '#lib/console/stage.js';
import { api, ApiError, type StageOrder } from '#lib/control/api.js';
import { live } from '#lib/control/live.svelte.js';
import { positionNow } from '#lib/control/state.js';
import { toasts } from '#lib/control/toasts.svelte.js';
import type { Content } from '#lib/control/types.js';
import { history } from '#lib/commands/undo.svelte.js';
import { i18n } from '#lib/i18n';

/** How long "play now" waits for the song to be cued before it gives up starting it. */
const CUE_WAIT = 20_000;

export function fail(error: unknown): void {
	const text = error instanceof Error ? error.message : String(error);
	toasts.show(i18n.t.app.failed(text), 'error');
}

export function queue(): Queue {
	return live.state.queue;
}

export function content(id: string): Content | undefined {
	return live.state.contents.find((c) => c.id === id);
}

/** Gives an order; the session it answers with is shown at once. */
async function ask(
	command: StageOrder['command'],
	extra: Omit<StageOrder, 'command'> = {}
): Promise<Session | null> {
	try {
		const session = await api.command({ command, ...extra });
		if (session.version >= live.state.session.version) live.state = { ...live.state, session };
		return session;
	} catch (error) {
		fail(error);
		return null;
	}
}

async function order(
	command: StageOrder['command'],
	extra: Omit<StageOrder, 'command'> = {}
): Promise<void> {
	await ask(command, extra);
}

/** Starts what is cued; if some screens are not ready, the operator decides. */
async function start(): Promise<void> {
	try {
		await api.command({ command: 'start' });
	} catch (error) {
		if (!(error instanceof ApiError && error.code === 'screens_not_ready')) {
			fail(error);
			return;
		}
		const ids = Array.isArray(error.body.screens) ? (error.body.screens as string[]) : [];
		const names = ids.map((id) => {
			const screen = live.state.screens.find((s) => s.id === id);
			return screen ? screenName(screen) : id;
		});
		if (window.confirm(i18n.t.stage.startAnyway(names.join(', ')))) {
			await order('start', { force: true });
		}
	}
}

/** Waits until the session is cued for `epoch` (the audio has the song ready). */
function cued(epoch: number): Promise<boolean> {
	return new Promise((resolve) => {
		const began = performance.now();
		const check = () => {
			const session = live.state.session;
			if (session.epoch === epoch && session.state === 'cued') resolve(true);
			else if (session.epoch !== epoch || performance.now() - began > CUE_WAIT) resolve(false);
			else setTimeout(check, 100);
		};
		check();
	});
}

const session = () => live.state.session;

export const transport = {
	/** Space: pause what plays, start what is cued, else get the next song ready. */
	toggle: () => {
		const state = session().state;
		if (state === 'playing') return order('pause');
		if (state === 'cued' || state === 'paused') return start();
		if (state === 'cueing') {
			toasts.show(i18n.t.stage.stillCueing);
			return;
		}
		return order('cue');
	},
	start,
	pause: () => order('pause'),
	next: () => order('next'),
	previous: () => order('previous'),
	stop: () => order('stop'),
	cue: (itemId: string) => order('cue', { item_id: itemId }),
	/** Cues the item and starts it as soon as the audio has it ready. */
	playItem: async (itemId: string) => {
		const cuedSession = await ask('cue', { item_id: itemId });
		if (cuedSession && (await cued(cuedSession.epoch))) await start();
	},
	seek: (position: number) => order('seek', { position: Math.max(0, position) }),
	seekBy: (seconds: number) => {
		const at = positionNow(session(), live.serverMicros()) ?? 0;
		return order('seek', { position: Math.max(0, at + seconds) });
	},
	restart: () => order('seek', { position: session().current?.item.start ?? 0 }),
	volume: (value: number) => order('volume', { value: Math.round(value * 100) / 100 }),
	volumeBy: (step: number) => transport.volume(session().volume + step),
	pitch: (value: number) => order('pitch', { value }),
	pitchBy: (step: number) => order('pitch', { value: session().semitones + step }),
	pitchReset: () => order('pitch', { value: 0 })
};

function setQueue(saved: Queue): void {
	if (saved.version >= live.state.queue.version) live.state = { ...live.state, queue: saved };
}

let editing: Promise<void> = Promise.resolve();

/**
 * Changes the queue's order or items: shown at once, saved with its version; on a conflict the
 * change is applied again to the newer queue. Undoable. Edits go one after another, each on the
 * queue the one before left: two at once (an undo and a typed singer) would each save over the
 * other.
 */
export function editQueue(
	label: string,
	change: (items: QueueItem[]) => QueueItem[]
): Promise<void> {
	const run = editing.then(() => saveEdit(label, change));
	editing = run.catch(() => {});
	return run;
}

async function saveEdit(label: string, change: (items: QueueItem[]) => QueueItem[]): Promise<void> {
	const from = queue();
	const before = from.items;
	const after = change(before);
	if (JSON.stringify(before) === JSON.stringify(after)) return;
	const revert = live.patch((state) => ({ ...state, queue: { ...from, items: after } }));
	const entry = {
		label,
		undo: async () => {
			await editQueue(label, () => before).then(() => void history.past.pop());
		},
		redo: async () => {
			await editQueue(label, change).then(() => void history.past.pop());
		}
	};
	history.push(entry);
	try {
		setQueue(await api.saveQueue({ ...from, items: after }));
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

/** Adds songs to the end of the queue (or right after the song on). */
export async function addToQueue(contentIds: string[], next = false): Promise<void> {
	if (!contentIds.length) return;
	const titles = contentIds.map((id) => content(id)?.title ?? id).join(', ');
	try {
		const saved = await api.addToQueue(contentIds.map((content_id) => ({ content_id })));
		setQueue(saved);
		if (next) {
			const fresh = saved.items.slice(-contentIds.length).map((i) => i.id);
			const on = session().current?.item.id;
			await editQueue(i18n.t.cmd.addNext, (items) => {
				const moving = items.filter((i) => fresh.includes(i.id));
				const rest = items.filter((i) => !fresh.includes(i.id));
				const at = rest.findIndex((i) => i.id === on);
				return [...rest.slice(0, at + 1), ...moving, ...rest.slice(at + 1)];
			});
		}
		toasts.show(i18n.t.library.added(titles));
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
	return editQueue(i18n.t.playback.dragHint, (items) => {
		const moving = items.find((i) => i.id === id);
		if (!moving || id === beforeId) return items;
		const rest = items.filter((i) => i.id !== id);
		const at = beforeId === null ? rest.length : rest.findIndex((i) => i.id === beforeId);
		return [...rest.slice(0, at), moving, ...rest.slice(at)];
	});
}

export function updateItem(id: string, change: Partial<QueueItem>): Promise<void> {
	return editQueue(i18n.t.playback.singer, (items) =>
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
