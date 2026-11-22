import { describe, expect, it } from 'vitest';
import type { Anchor, Program, Session } from '#lib/contracts';
import { initial, isReady, step, type Effect, type Event, type Model } from './machine';

const program = (id: string, manifest = id.repeat(64).slice(0, 64)): Program => ({
	item: {
		id,
		content_id: `song-${id}`,
		manifest: null,
		start: null,
		end: null,
		semitones: 0,
		singer: null
	},
	manifest,
	duration: 200
});

const A = program('a');
const B = program('b');

function session(over: Partial<Session> = {}): Session {
	return {
		version: 1,
		epoch: 1,
		state: 'cueing',
		current: A,
		anchor: { position: 2, instant: 1_000_000, rate: 0 },
		upcoming: [B],
		semitones: 0,
		volume: 1,
		...over
	};
}

/** Runs the events in order; returns the last model and every effect, flattened. */
function run(events: Event[], from: Model = initial()) {
	let model = from;
	const effects: Effect[] = [];
	for (const event of events) {
		const next = step(model, event);
		model = next.model;
		effects.push(...next.effects);
	}
	return { model, effects, kinds: effects.map((e) => e.kind) };
}

const prepared = (anchor: Anchor, epoch = 1, manifest = A.manifest): Event => ({
	type: 'prepared',
	manifest,
	epoch,
	anchor
});

describe('the screen state machine', () => {
	it('connects, has nothing on, then provisions, syncs and waits for the operator', () => {
		const cue = session();
		const idle = run([{ type: 'session', session: session({ current: null, anchor: null }) }]);
		expect(idle.model.state).toBe('idle');
		expect(idle.kinds).toContain('release');

		const { model, effects } = run([{ type: 'session', session: cue }], idle.model);
		expect(model.state).toBe('provisioning');
		expect(effects).toContainEqual({ kind: 'provision', program: A });
		expect(isReady(model)).toBe(false);

		const synced = run([{ type: 'cached', manifest: A.manifest }], model);
		expect(synced.model.state).toBe('syncing');
		expect(synced.effects).toContainEqual({
			kind: 'prepare',
			program: A,
			epoch: 1,
			anchor: cue.anchor
		});

		const waiting = run([prepared(cue.anchor!)], synced.model);
		expect(waiting.model.state).toBe('waiting');
		expect(isReady(waiting.model)).toBe(true);
		expect(waiting.kinds).toEqual(['report']);
	});

	it('a new layout checks the songs again and looks up the frame again', () => {
		const cue = session();
		const ready = run([
			{ type: 'session', session: cue },
			{ type: 'cached', manifest: A.manifest },
			prepared(cue.anchor!)
		]);
		expect(isReady(ready.model)).toBe(true);
		const { model, effects } = run([{ type: 'layout-changed' }], ready.model);
		// The video it now needs may not be here: the song is provisioned again.
		expect(model.state).toBe('provisioning');
		expect(model.cached.size).toBe(0);
		expect(isReady(model)).toBe(false);
		expect(effects).toContainEqual({ kind: 'provision', program: A });
		expect(effects).toContainEqual({ kind: 'prefetch', programs: [B] });

		const idle = run([
			{ type: 'session', session: session({ current: null, anchor: null }) },
			{ type: 'layout-changed' }
		]);
		expect(idle.model.state).toBe('idle');
	});

	it('a song already here goes straight to syncing, and what comes next is fetched', () => {
		const here = { ...initial(), cached: new Set([A.manifest]) };
		const { model, effects } = run([{ type: 'session', session: session() }], here);
		expect(model.state).toBe('syncing');
		expect(effects[0]).toEqual({ kind: 'prefetch', programs: [B] });
	});

	it('a start carries on from the frame: no new look-up, it plays at the instant', () => {
		const cue = session();
		const ready = run([
			{ type: 'session', session: cue },
			{ type: 'cached', manifest: A.manifest },
			prepared(cue.anchor!)
		]);
		const start = session({
			version: 2,
			state: 'playing',
			anchor: { position: 2, instant: 3_000_000, rate: 1 }
		});
		const armed = run([{ type: 'session', session: start }], ready.model);
		expect(armed.model.state).toBe('waiting');
		expect(armed.kinds).not.toContain('prepare');
		expect(isReady(armed.model)).toBe(true);
		const playing = run([{ type: 'moving' }], armed.model);
		expect(playing.model.state).toBe('playing');

		const pause = session({
			version: 3,
			state: 'paused',
			anchor: { position: 12, instant: 13_000_000, rate: 0 }
		});
		const paused = run([{ type: 'session', session: pause }, { type: 'stopped' }], playing.model);
		expect(paused.model.state).toBe('paused');
		expect(paused.kinds).not.toContain('prepare');
	});

	it('a seek or another song looks for the frame again; a late look-up is dropped', () => {
		const cue = session();
		const ready = run([
			{ type: 'session', session: cue },
			{ type: 'cached', manifest: A.manifest },
			prepared(cue.anchor!)
		]);
		const seek = session({ version: 2, anchor: { position: 60, instant: 2_000_000, rate: 0 } });
		const sought = run([{ type: 'session', session: seek }], ready.model);
		expect(sought.model.state).toBe('syncing');
		expect(sought.kinds).toContain('prepare');
		// The look-up for the old position comes back after the seek: it does not count.
		const stale = run([prepared(cue.anchor!)], sought.model);
		expect(stale.model.state).toBe('syncing');
		const fresh = run([prepared(seek.anchor!)], sought.model);
		expect(fresh.model.state).toBe('waiting');

		const next = session({ version: 3, epoch: 2, current: B, upcoming: [] });
		const other = run([{ type: 'session', session: next }], fresh.model);
		expect(other.model.state).toBe('provisioning');
		expect(other.effects).toContainEqual({ kind: 'provision', program: B });
	});

	it('joins a song half-way: it looks for the frame and plays at once', () => {
		const playing = session({
			state: 'playing',
			anchor: { position: 2, instant: 1_000_000, rate: 1 }
		});
		const here = { ...initial(), cached: new Set([A.manifest]) };
		const joined = run(
			[{ type: 'session', session: playing }, prepared(playing.anchor!), { type: 'moving' }],
			here
		);
		expect(joined.model.state).toBe('playing');
		expect(isReady(joined.model)).toBe(true);
	});

	it('losing sync while playing resyncs; losing the link mid-song keeps the picture', () => {
		const playing = session({
			state: 'playing',
			anchor: { position: 2, instant: 1_000_000, rate: 1 }
		});
		const here = { ...initial(), cached: new Set([A.manifest]) };
		const on = run(
			[{ type: 'session', session: playing }, prepared(playing.anchor!), { type: 'moving' }],
			here
		);
		expect(run([{ type: 'link-lost' }], on.model).model.state).toBe('playing');
		const lost = run([{ type: 'lost-sync' }], on.model);
		expect(lost.model.state).toBe('syncing');
		expect(lost.kinds).toContain('prepare');
		expect(run([{ type: 'link-lost' }]).model.state).toBe('connecting');
	});

	it('an older session never undoes a newer one, and an error only ends with a reload', () => {
		const newer = run([{ type: 'session', session: session({ version: 5 }) }]);
		const older = run(
			[{ type: 'session', session: session({ version: 4, current: null, anchor: null }) }],
			newer.model
		);
		expect(older.model.state).toBe('provisioning');
		const broken = run([{ type: 'fatal', error: 'no H.264 here' }], newer.model);
		expect(broken.model.state).toBe('error');
		expect(
			run([{ type: 'session', session: session({ version: 9 }) }], broken.model).model.state
		).toBe('error');
	});

	it('a failed download is reported while the screen keeps trying', () => {
		const { model } = run([{ type: 'session', session: session() }]);
		const failed = run([{ type: 'provision-failed', manifest: A.manifest, error: 'quota' }], model);
		expect(failed.model.state).toBe('provisioning');
		expect(failed.model.error).toBe('quota');
	});

	it('the end of a song waits for the next cue', () => {
		const playing = session({
			state: 'playing',
			anchor: { position: 190, instant: 1_000_000, rate: 1 }
		});
		const here = { ...initial(), cached: new Set([A.manifest]) };
		const on = run(
			[{ type: 'session', session: playing }, prepared(playing.anchor!), { type: 'moving' }],
			here
		);
		const ended = session({
			version: 2,
			state: 'ended',
			anchor: { position: 200, instant: 11_000_000, rate: 0 }
		});
		expect(
			run([{ type: 'session', session: ended }, { type: 'stopped' }], on.model).model.state
		).toBe('waiting');
	});
});
