/**
 * The screens' sync bench (decision 011): the web side of `kp-syncbench`.
 *
 * It simulates what a screen meets on a real LAN and runs the screen's own code — `ServerClock`
 * and `VideoFollower` — against the truth the simulation knows: the server's clock (which the
 * audio follows, kp-syncbench checks that), a screen whose crystal drifts, a network with
 * jitter and Wi-Fi spikes, a display with its refresh rate and a `<video>` that only lets itself
 * be steered by speed and by jumps that take time.
 *
 * Targets, against what the audio plays at the instant each frame is shown: the video frame
 * shown holds the audio heard (on a cable, always at p95; never more than a frame off), and the
 * lyrics follow it within a millisecond or two. A Wi-Fi with jitter and spikes is allowed a few
 * ms more: that much is the network's, not the screen's.
 */
import { describe, expect, it } from 'vitest';
import type { Anchor } from '#lib/contracts';
import { ServerClock } from './clock';
import { VideoFollower } from './servo';
import { positionAt } from './timeline';

/** Deterministic random numbers (xorshift32), so every run is the same. */
function random(seed: number) {
	let x = seed || 1;
	return () => {
		x ^= x << 13;
		x ^= x >>> 17;
		x ^= x << 5;
		return (x >>> 0) / 2 ** 32;
	};
}

interface Scenario {
	name: string;
	seconds: number;
	/** The screen's crystal against the server's. */
	ppm: number;
	refreshHz: number;
	fps: number;
	/** One-way delay and its jitter, in ms; a share of the packets is late by `spikeMs`. */
	delayMs: number;
	jitterMs: number;
	spikes: number;
	spikeMs: number;
	/** How long a `<video>` jump takes, in ms. */
	seekMs: number;
	/** The screen joins this long after the song started (0: it was there at the start). */
	joinSeconds: number;
	/** p95 targets, in ms: the picture outside the frame being heard, and the lyrics. */
	avP95: number;
	lyricsP95: number;
}

function simulate(s: Scenario) {
	const rand = random(7);
	const local = (t: number) => t * (1 + s.ppm * 1e-6) + 123_456_789; // the screen's µs
	const oneWay = () =>
		(s.delayMs + rand() * s.jitterMs + (rand() < s.spikes ? s.spikeMs : 0)) * 1000;
	// The song starts at true (= server) 2 s from position 0.
	const anchor: Anchor = { position: 0, instant: 2e6, rate: 1 };
	const heard = (t: number) => positionAt(anchor, t);

	const clock = new ServerClock();
	const follower = new VideoFollower();
	const span = 1 / s.fps;
	const frame = 1e6 / (s.refreshHz * (1 + s.ppm * 1e-6)); // the display runs on the screen's crystal
	let media = 0; // the video's own position (s)
	let rate = 1;
	let seekingUntil = -1;
	let seekTo = 0;
	let started = false;
	const av: number[] = [];
	const lyrics: number[] = [];
	let jumps = 0;

	const start = s.joinSeconds * 1e6;
	// A burst of eight time requests on connecting, then one every two seconds.
	const pings: number[] = [];
	for (let i = 0; i < 8; i++) pings.push(start + i * 20_000);
	for (let t = start + 2e6; t < s.seconds * 1e6; t += 2e6) pings.push(t);

	let last = start;
	for (let t = start; t < s.seconds * 1e6; t += frame) {
		while (pings.length && pings[0] <= t) {
			const sent = pings.shift() as number;
			const there = sent + oneWay();
			const back = there + oneWay();
			clock.observe(there, local(sent), local(back));
		}
		const dt = (t - last) / 1e6;
		last = t;
		// The video moves on the screen's own clock, at the speed it was given.
		if (started && t >= seekingUntil) {
			if (seekingUntil > 0) {
				media = seekTo;
				follower.seeked(s.seekMs / 1000);
				seekingUntil = -1;
			} else media += rate * dt * (1 + s.ppm * 1e-6);
		}
		if (!clock.ready) continue;
		// The frame drawn now is shown at the next vsync.
		const present = t + frame;
		const target = positionAt(anchor, clock.toServer(local(present)));
		const truth = heard(present);
		if (!started) {
			if (target <= 0) continue;
			// Late join or the start: jump to where the song will be once the jump is done.
			started = true;
			seekTo = positionAt(anchor, clock.toServer(local(t + s.seekMs * 1000))) + span / 2;
			seekingUntil = t + s.seekMs * 1000;
			continue;
		}
		if (seekingUntil > 0) continue;
		const shown = Math.floor(media * s.fps) / s.fps;
		const steer = follower.frame(shown, span, target);
		if (steer.kind === 'seek') {
			jumps++;
			seekTo = target + steer.ahead;
			seekingUntil = t + s.seekMs * 1000;
		} else rate = steer.rate;
		if (t < start + 10e6) continue; // the first seconds settle
		av.push(truth < shown ? shown - truth : truth > shown + span ? truth - shown - span : 0);
		lyrics.push(Math.abs(target - truth));
	}
	const pct = (xs: number[], p: number) => {
		const sorted = [...xs].sort((a, b) => a - b);
		return sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * p))] * 1000;
	};
	return {
		avP95: pct(av, 0.95),
		avMax: pct(av, 1),
		lyricsP95: pct(lyrics, 0.95),
		jumps,
		frameMs: 1000 / s.fps
	};
}

const base: Scenario = {
	name: 'wired, 60 Hz, 30 fps',
	seconds: 180,
	ppm: 60,
	refreshHz: 60,
	fps: 30,
	delayMs: 0.4,
	jitterMs: 0.6,
	spikes: 0,
	spikeMs: 0,
	seekMs: 120,
	joinSeconds: 0,
	avP95: 0,
	lyricsP95: 1
};

const scenarios: Scenario[] = [
	base,
	{ ...base, name: 'Wi-Fi with spikes, 50 Hz TV, 25 fps', ppm: -120, refreshHz: 50, fps: 25,
		delayMs: 2, jitterMs: 6, spikes: 0.15, spikeMs: 60, seekMs: 250, avP95: 2, lyricsP95: 4 }, // prettier-ignore
	{ ...base, name: 'a Raspberry Pi joining half-way', ppm: 150, fps: 30, seekMs: 400,
		joinSeconds: 45 } // prettier-ignore
];

describe('screens keep in step with the audio', () => {
	for (const scenario of scenarios) {
		it(scenario.name, () => {
			const result = simulate(scenario);
			expect(result.avP95, 'the frame shown holds the audio heard').toBeLessThanOrEqual(
				scenario.avP95
			);
			expect(result.avMax, 'never more than a frame off').toBeLessThan(result.frameMs);
			expect(result.lyricsP95, 'the lyrics follow the sound').toBeLessThan(scenario.lyricsP95);
			expect(result.jumps, 'it settles without jumping').toBeLessThanOrEqual(1);
		});
	}
});
