import { describe, expect, it } from 'vitest';
import { BURST, ServerClock } from './clock';
import { sha256Hex, Sha256 } from './sha256';
import { DEADBAND, HARD, MAX_TRIM, learnLag, p95Ms, steer } from './servo';
import { continuous, endOf, movingAt, positionAt } from './timeline';

describe('the server clock', () => {
	it('keeps the answer with the shortest round trip', () => {
		const clock = new ServerClock();
		// Server = local + 5 s. A 40 ms answer, then a 2 ms one, then a 30 ms one.
		clock.observe(5_000_000 + 20_000, 0, 40_000);
		clock.observe(5_000_000 + 101_000, 100_000, 102_000);
		clock.observe(5_000_000 + 215_000, 200_000, 230_000);
		expect(clock.ready).toBe(true);
		expect(clock.rttMs).toBe(2);
		expect(clock.target(230_000)).toBeCloseTo(5_000_000, -1);
	});

	it('slews small corrections and snaps big ones', () => {
		const clock = new ServerClock();
		// The burst on connecting sets the offset outright: 1 000 000, rtt 2 ms.
		for (let i = 0; i < BURST; i++) clock.observe(1_000_000 + 1_000, 0, 2_000);
		expect(clock.offsetAt(2_000)).toBe(1_000_000);
		// A better answer (1 ms round trip) says 2 ms more: reached at 0.5 ms per second.
		clock.observe(1_000_500 + 1_002_000, 1_000_000, 1_001_000);
		const after1s = clock.offsetAt(3_000_000);
		expect(after1s).toBeGreaterThan(1_000_000);
		expect(after1s).toBeLessThan(1_002_000);
		expect(clock.offsetAt(10_000_000)).toBeCloseTo(1_002_000, -1);
		// The laptop slept: two seconds off are set at once.
		clock.observe(20_000_250 + 3_012_000, 20_000_000, 20_000_500);
		expect(clock.offsetAt(20_000_500)).toBe(3_012_000);
	});

	it('starts over on a new connection (a restarted server counts from elsewhere)', () => {
		const clock = new ServerClock();
		for (let t = 0; t <= 40e6; t += 2e6) clock.observe(t + 5e6 + 1_000, t, t + 2_000);
		clock.reset();
		expect(clock.ready).toBe(false);
		clock.observe(42e6 + 9e9 + 1_000, 42e6, 42e6 + 2_000);
		expect(clock.offsetAt(42e6 + 2_000)).toBe(9e9);
		expect(clock.driftPpm).toBe(0);
	});

	it('learns the drift between the crystals and follows it between answers', () => {
		const clock = new ServerClock();
		const ppm = 80;
		for (let t = 0; t <= 120e6; t += 2e6) {
			const server = t * (1 + ppm * 1e-6) + 7e6;
			clock.observe(server + 1_000, t, t + 2_000);
		}
		expect(clock.driftPpm).toBeCloseTo(ppm, 0);
		// 20 s after the last answer, the offset has moved on by the drift.
		const later = 140e6;
		const truth = later * (1 + ppm * 1e-6) + 7e6 - later;
		expect(Math.abs((clock.target(later) ?? 0) - truth)).toBeLessThan(300);
	});
});

describe('the timeline', () => {
	const anchor = { position: 10, instant: 1_000_000, rate: 1 };
	it('moves from the anchor and holds inside the song', () => {
		expect(positionAt(anchor, 500_000)).toBe(10);
		expect(positionAt(anchor, 3_500_000)).toBe(12.5);
		expect(positionAt(anchor, 100e6, 50)).toBe(50);
		expect(movingAt(anchor, 999_999)).toBe(false);
		expect(movingAt(anchor, 1_000_000)).toBe(true);
	});
	it('tells a start or a pause from a jump', () => {
		expect(continuous(anchor, { position: 12, instant: 3_000_000, rate: 0 })).toBe(true);
		expect(continuous(anchor, { position: 40, instant: 3_000_000, rate: 1 })).toBe(false);
	});
	it('ends at the exit point', () => {
		const item = {
			id: 'a',
			content_id: 'a',
			manifest: null,
			start: null,
			singer: null,
			semitones: 0
		};
		expect(endOf({ item: { ...item, end: 30 }, manifest: 'm', duration: 200 })).toBe(30);
		expect(endOf({ item: { ...item, end: null }, manifest: 'm', duration: 200 })).toBe(200);
	});
});

describe('the video servo', () => {
	it('leaves a picture on time alone, trims a small gap and jumps a big one', () => {
		expect(steer(0.005, 0)).toEqual({ kind: 'rate', rate: 1 });
		const behind = steer(-0.06, 0);
		expect(behind.kind).toBe('rate');
		if (behind.kind === 'rate') expect(behind.rate).toBeGreaterThan(1);
		const ahead = steer(HARD - 0.001, 0);
		if (ahead.kind === 'rate') expect(ahead.rate).toBeGreaterThanOrEqual(1 - MAX_TRIM);
		expect(steer(0.4, 0.08)).toEqual({ kind: 'seek', ahead: 0.08 });
		expect(steer(Number.NaN, 0).kind).toBe('seek');
		expect(DEADBAND).toBeLessThan(1 / 60);
	});
	it('learns how long a jump takes and reports the 95th percentile', () => {
		expect(learnLag(0, 0.1)).toBe(0.1);
		expect(learnLag(0.1, 0.2)).toBeCloseTo(0.13);
		expect(p95Ms([])).toBeNull();
		expect(p95Ms(Array.from({ length: 100 }, (_, i) => i / 1000))).toBe(95);
	});
});

describe('SHA-256', () => {
	const text = (s: string) => new TextEncoder().encode(s);
	it('matches the standard vectors', () => {
		expect(sha256Hex(text(''))).toBe(
			'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
		);
		expect(sha256Hex(text('abc'))).toBe(
			'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
		);
		expect(sha256Hex(text('abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq'))).toBe(
			'248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'
		);
	});
	it('gives the same hash however the bytes arrive', () => {
		const bytes = new Uint8Array(100_003).map((_, i) => (i * 31) & 0xff);
		const whole = sha256Hex(bytes);
		const pieces = new Sha256();
		for (let at = 0; at < bytes.length; at += 777) pieces.update(bytes.subarray(at, at + 777));
		expect(pieces.hex()).toBe(whole);
	});
});
