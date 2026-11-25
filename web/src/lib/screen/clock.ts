/**
 * The server's clock, as a screen learns it (decision 011).
 *
 * Every instant the stage talks about (an anchor, a `time` answer) is in µs on the server's
 * monotonic clock. A screen asks the time over its socket; an answer with a short round trip
 * says the offset well, a slow one (Wi-Fi, a busy tab) says little. So only the quickest answer
 * of every ten seconds counts, and the line through those (least squares, over the last five
 * minutes) gives both the offset and how fast the two crystals drift apart (tens of ppm).
 * Before there are three such answers, the quickest one of the last ten seconds is used.
 *
 * A new offset never jumps the picture: it is slewed at most `SLEW` (0.5 ms per second, which
 * nobody sees), unless it is far off (`SNAP`), as after the laptop slept. The first `BURST`
 * answers (asked all at once on connecting) set it outright: nothing is on screen yet.
 */

/** This page's monotonic clock in µs. */
export const localMicros = (): number => performance.now() * 1000;

interface Sample {
	/** Local µs half-way through the round trip. */
	at: number;
	rtt: number;
	offset: number;
}

/** One answer counts per bin: the quickest. */
const BIN = 10e6;
/** Bins the line is drawn through. */
const HISTORY = 300e6;
/** µs of correction per µs of local time: 500 ppm. */
const SLEW = 0.0005;
/** Further off than this, the offset is set at once. */
const SNAP = 50_000;
/** Answers that set the offset outright, before it is slewed. */
export const BURST = 8;

export class ServerClock {
	#bins = new Map<number, Sample>();
	#recent: Sample[] = [];
	#line: { a: number; b: number; origin: number } | null = null;
	#applied: number | null = null;
	#appliedAt = 0;
	#answers = 0;

	/** Forgets everything: a new connection may be to a restarted server, on another base. */
	reset(): void {
		this.#bins.clear();
		this.#recent = [];
		this.#line = null;
		this.#applied = null;
		this.#answers = 0;
	}

	/** A `time` answer: the server's `now`, and when the request left and the answer came. */
	observe(serverNow: number, sent: number, received: number): void {
		this.#answers++;
		const rtt = Math.max(0, received - sent);
		const sample = { at: sent + rtt / 2, rtt, offset: serverNow - (sent + rtt / 2) };
		this.#recent = [...this.#recent.filter((s) => received - s.at < BIN), sample];
		const bin = Math.floor(sample.at / BIN);
		const held = this.#bins.get(bin);
		if (!held || rtt < held.rtt) this.#bins.set(bin, sample);
		for (const key of this.#bins.keys()) {
			if (received - key * BIN > HISTORY) this.#bins.delete(key);
		}
		this.#line = fit([...this.#bins.values()]);
		if (this.#applied === null) {
			this.#applied = sample.offset;
			this.#appliedAt = received;
		}
	}

	/** Three answers are enough to trust it. */
	get ready(): boolean {
		return this.#answers >= 3;
	}

	/** The shortest recent round trip, in ms. */
	get rttMs(): number | null {
		if (!this.#recent.length) return null;
		return Math.min(...this.#recent.map((s) => s.rtt)) / 1000;
	}

	/** The server's clock against this one, in ppm (0 until it is known). */
	get driftPpm(): number {
		return (this.#line?.b ?? 0) * 1e6;
	}

	/** The offset (server µs minus local µs) the answers give for local instant `local`. */
	target(local: number): number | null {
		if (this.#line) return this.#line.a + this.#line.b * (local - this.#line.origin);
		if (!this.#recent.length) return null;
		return this.#recent.reduce((a, b) => (b.rtt < a.rtt ? b : a)).offset;
	}

	/** The offset at `local`, moved towards the target no faster than `SLEW`. */
	offsetAt(local: number): number {
		const target = this.target(local);
		if (target === null || this.#applied === null) return 0;
		const gap = target - this.#applied;
		const step = SLEW * Math.max(0, local - this.#appliedAt);
		const settling = this.#answers <= BURST;
		if (settling || Math.abs(gap) > SNAP || Math.abs(gap) <= step) this.#applied = target;
		else this.#applied += Math.sign(gap) * step;
		this.#appliedAt = local;
		return this.#applied;
	}

	toServer(local: number): number {
		return local + this.offsetAt(local);
	}
}

/** Least squares through the bins' quickest answers; none until three bins span 20 s. */
function fit(samples: Sample[]): { a: number; b: number; origin: number } | null {
	if (samples.length < 3) return null;
	const origin = samples[0].at;
	const n = samples.length;
	const mx = samples.reduce((s, p) => s + (p.at - origin), 0) / n;
	const my = samples.reduce((s, p) => s + p.offset, 0) / n;
	let num = 0;
	let den = 0;
	for (const p of samples) {
		num += (p.at - origin - mx) * (p.offset - my);
		den += (p.at - origin - mx) ** 2;
	}
	if (den <= 0) return null;
	const b = num / den;
	return { a: my - b * mx, b, origin };
}
