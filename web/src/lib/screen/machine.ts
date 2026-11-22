/**
 * A screen's state machine (decision 011): a pure reducer, `step(model, event)`, that says what
 * state the screen is in and what has to happen next. The runtime does the effects (download,
 * look for a frame, send the status) and feeds what came of them back as events, so every path
 * — a cue, a start, joining a song half-way, a reconnection — is plain data the tests drive.
 *
 * ```
 * connecting ──session──► idle ──cue──► provisioning ──cached──► syncing ──prepared──► waiting
 *                                                                   ▲                    │ moving
 *                                     lost-sync / a jump ───────────┤                    ▼
 *                                                                   └──────────────── playing ⇄ paused
 * error: only a reload leaves it.
 * ```
 *
 * The server's session is the truth: the screen catches up with the newest one it gets. A
 * change that carries on from where the picture is (a start, a pause, the end of the song) only
 * starts or stops it; anything else (another song, a seek) looks for the frame again.
 */
import type { Anchor, Program, ScreenStatus, Session } from '#lib/contracts';
import { continuous } from './timeline';

export type ScreenState = ScreenStatus['state'];

export interface Prepared {
	manifest: string;
	epoch: number;
	anchor: Anchor;
}

export interface Model {
	state: ScreenState;
	session: Session | null;
	/** Manifests whose blobs are all here and checked. */
	cached: ReadonlySet<string>;
	/** What the picture is on: the song, the epoch and the anchor it was looked up at. */
	prepared: Prepared | null;
	error: string | null;
}

export type Event =
	| { type: 'link-lost' }
	| { type: 'session'; session: Session }
	| { type: 'cached'; manifest: string }
	| { type: 'provision-failed'; manifest: string; error: string }
	| { type: 'prepared'; manifest: string; epoch: number; anchor: Anchor }
	/** The anchor's instant came and the song moves. */
	| { type: 'moving' }
	/** The anchor's instant came and the song holds. */
	| { type: 'stopped' }
	/** The picture fell too far off (or the page was hidden): look for the frame again. */
	| { type: 'lost-sync' }
	| { type: 'fatal'; error: string };

export type Effect =
	| { kind: 'provision'; program: Program }
	| { kind: 'prefetch'; programs: Program[] }
	| { kind: 'prepare'; program: Program; epoch: number; anchor: Anchor }
	| { kind: 'release' }
	| { kind: 'report' };

export interface Step {
	model: Model;
	effects: Effect[];
}

export const initial = (): Model => ({
	state: 'connecting',
	session: null,
	cached: new Set(),
	prepared: null,
	error: null
});

/** Whether the picture is on the cued frame for the session's epoch: what `ready` reports. */
export function isReady(model: Model): boolean {
	const { prepared, session } = model;
	return (
		prepared !== null &&
		session !== null &&
		prepared.epoch === session.epoch &&
		['waiting', 'playing', 'paused'].includes(model.state)
	);
}

const report: Effect = { kind: 'report' };

export function step(model: Model, event: Event): Step {
	if (model.state === 'error') return { model, effects: [] };
	switch (event.type) {
		case 'fatal':
			return { model: { ...model, state: 'error', error: event.error }, effects: [report] };
		case 'link-lost':
			// Mid-song the picture goes on with the last anchor; with nothing on it waits.
			return model.session?.current
				? { model, effects: [] }
				: { model: { ...model, state: 'connecting' }, effects: [] };
		case 'session':
			return follow(model, event.session);
		case 'cached':
			return cached(model, event.manifest);
		case 'provision-failed':
			return model.session?.current?.manifest === event.manifest
				? { model: { ...model, error: event.error }, effects: [report] }
				: { model, effects: [] };
		case 'prepared':
			return prepared(model, event);
		case 'moving':
			return ['waiting', 'paused'].includes(model.state)
				? { model: { ...model, state: 'playing' }, effects: [report] }
				: { model, effects: [] };
		case 'stopped':
			return model.state === 'playing'
				? { model: { ...model, state: held(model.session) }, effects: [report] }
				: { model, effects: [] };
		case 'lost-sync':
			return model.state === 'playing' ? lookAgain(model) : { model, effects: [] };
	}
}

/** Paused mid-song, or waiting for the operator (a cue, the end of a song). */
function held(session: Session | null): ScreenState {
	return session?.state === 'paused' ? 'paused' : 'waiting';
}

function follow(model: Model, session: Session): Step {
	const before = model.session;
	if (before && session.version < before.version) return { model, effects: [] };
	const effects: Effect[] = [];
	if (!before || JSON.stringify(before.upcoming) !== JSON.stringify(session.upcoming)) {
		effects.push({ kind: 'prefetch', programs: session.upcoming });
	}
	const { current, anchor } = session;
	if (!current || !anchor) {
		return {
			model: { ...model, session, state: 'idle', prepared: null, error: null },
			effects: [...effects, { kind: 'release' }, report]
		};
	}
	const on = model.prepared;
	const sameSong =
		on?.manifest === current.manifest && before?.current?.item.id === current.item.id;
	if (on && sameSong && continuous(on.anchor, anchor)) {
		// A start, a pause, the end, a new epoch for the same frame: the picture stays.
		const prepared = { ...on, epoch: session.epoch, anchor };
		return { model: { ...model, session, prepared }, effects: [...effects, report] };
	}
	return lookAgain({ ...model, session }, effects);
}

/** Another song or a jump: download it if it is not here, else look for its frame. */
function lookAgain(model: Model, effects: Effect[] = []): Step {
	const session = model.session;
	if (!session?.current || !session.anchor) return { model, effects };
	const program = session.current;
	if (!model.cached.has(program.manifest)) {
		return {
			model: { ...model, state: 'provisioning', prepared: null, error: null },
			effects: [...effects, { kind: 'provision', program }, report]
		};
	}
	return {
		model: { ...model, state: 'syncing', prepared: null, error: null },
		effects: [
			...effects,
			{ kind: 'prepare', program, epoch: session.epoch, anchor: session.anchor },
			report
		]
	};
}

function cached(model: Model, manifest: string): Step {
	const next = { ...model, cached: new Set([...model.cached, manifest]) };
	if (model.state === 'provisioning' && model.session?.current?.manifest === manifest) {
		return lookAgain(next);
	}
	return { model: next, effects: [] };
}

function prepared(model: Model, event: Extract<Event, { type: 'prepared' }>): Step {
	const session = model.session;
	const fits =
		model.state === 'syncing' &&
		session?.current?.manifest === event.manifest &&
		session.epoch === event.epoch &&
		session.anchor !== null &&
		continuous(event.anchor, session.anchor);
	if (!fits || !session?.anchor) return { model, effects: [] }; // a look-up the session outran
	const on = { manifest: event.manifest, epoch: event.epoch, anchor: session.anchor };
	return { model: { ...model, prepared: on, state: held(session) }, effects: [report] };
}
