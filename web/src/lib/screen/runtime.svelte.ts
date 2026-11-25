/**
 * A web screen at work (decision 011): it keeps its line to the stage, learns the server's
 * clock, runs the state machine (`machine.ts`) and does what the machine asks — download a song,
 * look for its frame, show it — and keeps the `<video>` on the timeline frame by frame.
 *
 * Two `<video>` elements take turns: while one shows the song on, the other already holds the
 * next one, stopped on its first frame, so the next cue only has to swap them.
 */
import type {
	ContentCache,
	KaraokeDoc,
	Lyrics,
	Manifest,
	ManifestTrack,
	PlaybackClock,
	Program,
	ScreenConfig,
	ScreenHello,
	ScreenStatus,
	Session
} from '#lib/contracts';
import { docFromTracks } from '#lib/lyrics';
import { BURST, ServerClock, localMicros } from './clock';
import type { FetchReply, FetchRequest } from './fetcher.worker';
import { initial, isReady, step, type Effect, type Event, type Model } from './machine';
import { VideoFollower, p95Ms } from './servo';
import { openStore, type BlobStore } from './store';
import { endOf, movingAt, positionAt } from './timeline';

const TIME_EVERY = 2000;
const STATUS_EVERY = 1000;
/** Frames whose error is kept for the p95 the screen reports. */
const ERRORS_KEPT = 180;
/** More jumps than this in `JUMP_WINDOW` ms: the video cannot keep up (`degraded`). */
const JUMPS_TOO_MANY = 3;
const JUMP_WINDOW = 10_000;

export const DEFAULT_CONFIG: ScreenConfig = {
	name: null,
	layout: 'video-lyrics',
	theme: 'clasico',
	display_ms: 0,
	video_max_height: null
};

export interface Song {
	program: Program;
	manifest: Manifest;
	doc: KaraokeDoc | null;
	video: ManifestTrack | null;
}

type Codec = ScreenHello['codecs'][number];
const PROBES: Record<Codec, string> = {
	h264: 'video/mp4; codecs="avc1.640028"',
	hevc: 'video/mp4; codecs="hvc1.1.6.L120.90"',
	av1: 'video/mp4; codecs="av01.0.08M.08"'
};

/** The video codecs this browser plays. */
export function playableCodecs(probe: (type: string) => string): Codec[] {
	return (Object.keys(PROBES) as Codec[]).filter((codec) => probe(PROBES[codec]) !== '');
}

/**
 * The video track to download: the smallest one at least as tall as the screen, among the
 * codecs it plays and no taller than its limit; else the tallest that fits.
 */
export function chooseVideo(
	manifest: Manifest,
	codecs: readonly Codec[],
	screenHeight: number,
	limit: number | null
): ManifestTrack | null {
	const videos = manifest.tracks
		.filter((t) => t.kind === 'video' && t.video && codecs.includes(t.video.codec))
		.filter((t) => limit === null || (t.video?.height ?? 0) <= limit)
		.sort((a, b) => (a.video?.height ?? 0) - (b.video?.height ?? 0));
	return videos.find((t) => (t.video?.height ?? 0) >= screenHeight) ?? videos.at(-1) ?? null;
}

/** The id this screen goes by: `?screen=` if given, else one this browser keeps. */
function screenId(): string {
	const given = new URLSearchParams(location.search).get('screen');
	if (given) return given;
	try {
		const tab = sessionStorage.getItem('karaoke.screen.tab');
		if (tab) return tab;
		let id = localStorage.getItem('karaoke.screen');
		if (!id) {
			id = `s-${crypto.getRandomValues(new Uint32Array(1))[0].toString(16)}`;
			localStorage.setItem('karaoke.screen', id);
		}
		return id;
	} catch {
		return `s-${Math.floor(Math.random() * 2 ** 32).toString(16)}`;
	}
}

export class ScreenRuntime {
	model = $state.raw<Model>(initial());
	config = $state.raw<ScreenConfig>(DEFAULT_CONFIG);
	connected = $state(false);
	hidden = $state(false);
	fullscreen = $state(false);
	degraded = $state(false);
	/** The song on screen, once it is prepared. */
	song = $state.raw<Song | null>(null);
	/** Title and artist of each song the session names, by manifest, for the waiting screen. */
	titles = $state.raw<Record<string, { title: string; artist: string | null }>>({});
	/** Downloads, by manifest. */
	progress = $state.raw<Record<string, ContentCache>>({});
	/** Which `<video>` is showing. */
	active = $state(0);

	readonly clock = new ServerClock();
	readonly id: string;
	readonly preview: boolean;
	/** For the lyrics: the song position at the instant the next frame is shown. */
	readonly lyricsClock: PlaybackClock = { now: () => this.#songAt(this.#presented()) };

	#socket: WebSocket | null = null;
	#stopped = true;
	#retry = 500;
	#timers: ReturnType<typeof setInterval>[] = [];
	#frame = 0;
	#wake: ReturnType<typeof setTimeout> | undefined = undefined;
	#frameMs = 1000 / 60;
	#lastTick = 0;
	#store: BlobStore | null = null;
	#worker: Worker | null = null;
	// Plain (not reactive): the runtime's own bookkeeping, which nothing renders from.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	#requests = new Map<
		number,
		{
			done: (inMemory: Blob | null) => void;
			failed: (error: Error) => void;
			progress: (n: number) => void;
		}
	>();
	#nextRequest = 1;
	// Plain (not reactive): the runtime's own bookkeeping, which nothing renders from.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	#memory = new Map<string, Blob>();
	// Plain (not reactive): the runtime's own bookkeeping, which nothing renders from.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	#manifests = new Map<string, Manifest>();
	// Plain (not reactive): the runtime's own bookkeeping, which nothing renders from.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	#provisions = new Map<string, Promise<void>>();
	#slots: (HTMLVideoElement | null)[] = [null, null];
	#slotSong: (string | null)[] = [null, null];
	#urls: (string | null)[] = [null, null];
	#loads: (Promise<HTMLVideoElement> | null)[] = [null, null];
	/** The frame callback each element has pending, and when the one on screen last ran. */
	#armed: (number | null)[] = [null, null];
	#lastFrame = 0;
	#follower = new VideoFollower();
	#errors: number[] = [];
	#jumps: number[] = [];
	#seeking = false;
	#prepareToken = 0;
	#codecs: Codec[] = ['h264'];

	constructor(options: { preview?: boolean } = {}) {
		this.id = screenId();
		this.preview = options.preview ?? false;
	}

	// Life

	async start(): Promise<void> {
		if (!this.#stopped) return;
		this.#stopped = false;
		this.#store = await openStore();
		try {
			// The worker's address for the bundler, not state.
			// eslint-disable-next-line svelte/prefer-svelte-reactivity
			this.#worker = new Worker(new URL('./fetcher.worker.ts', import.meta.url), {
				type: 'module'
			});
			this.#worker.onmessage = (message: MessageEvent<FetchReply>) => this.#reply(message.data);
		} catch {
			this.#worker = null; // downloads then run on the page
		}
		this.#codecs = playableCodecs((type) => document.createElement('video').canPlayType(type));
		this.#connect();
		this.#timers.push(setInterval(() => this.#askTime(), TIME_EVERY));
		this.#timers.push(
			setInterval(() => {
				this.#follow();
				this.#report();
			}, STATUS_EVERY)
		);
		document.addEventListener('visibilitychange', this.#visibility);
		document.addEventListener('fullscreenchange', this.#fullscreenChange);
		this.#frame = requestAnimationFrame(this.#tick);
	}

	stop(): void {
		this.#stopped = true;
		for (const timer of this.#timers) clearInterval(timer);
		this.#timers = [];
		cancelAnimationFrame(this.#frame);
		clearTimeout(this.#wake);
		document.removeEventListener('visibilitychange', this.#visibility);
		document.removeEventListener('fullscreenchange', this.#fullscreenChange);
		this.#socket?.close();
		this.#socket = null;
		this.#worker?.terminate();
		for (const url of this.#urls) if (url) URL.revokeObjectURL(url);
	}

	/** The two `<video>` elements, from the view. */
	attach(a: HTMLVideoElement, b: HTMLVideoElement): void {
		this.#slots = [a, b];
		this.#arm(0);
		this.#arm(1);
	}

	// The state machine

	dispatch(event: Event): void {
		const { model, effects } = step(this.model, event);
		this.model = model;
		for (const effect of effects) this.#run(effect);
	}

	#run(effect: Effect): void {
		switch (effect.kind) {
			case 'provision':
				void this.#provisionCurrent(effect.program);
				break;
			case 'prefetch':
				void this.#prefetch(effect.programs);
				break;
			case 'prepare':
				void this.#prepare(effect.program, effect.epoch, effect.anchor);
				break;
			case 'release':
				this.song = null;
				for (const element of this.#slots) element?.pause();
				break;
			case 'report':
				this.#report();
				break;
		}
	}

	get session(): Session | null {
		return this.model.session;
	}

	#needsVideo(): boolean {
		return this.config.layout === 'video-lyrics' || this.config.layout === 'video';
	}

	// The line to the stage

	#connect(): void {
		const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
		const socket = new WebSocket(`${scheme}://${location.host}/api/screens/ws`);
		this.#socket = socket;
		socket.onopen = () => {
			this.connected = true;
			this.#retry = 500;
			this.clock.reset();
			socket.send(JSON.stringify({ type: 'hello', hello: this.#hello() }));
			// A burst of time requests: the quickest of them sets the clock before anything shows.
			for (let i = 0; i < BURST; i++) setTimeout(() => this.#askTime(), i * 25);
		};
		socket.onmessage = (message) =>
			this.#message(JSON.parse(String(message.data)) as { type: string } & Record<string, unknown>);
		socket.onclose = (closed) => {
			if (this.#socket !== socket) return;
			this.connected = false;
			this.dispatch({ type: 'link-lost' });
			if (closed.code === 4009) {
				// Another tab of this browser is this screen: this one becomes another.
				try {
					sessionStorage.setItem(
						'karaoke.screen.tab',
						`${this.id}-${Math.floor(Math.random() * 65536).toString(16)}`
					);
				} catch {
					// without storage it keeps trying with the same id
				}
				location.reload();
				return;
			}
			if (this.#stopped) return;
			setTimeout(() => this.#connect(), this.#retry);
			this.#retry = Math.min(this.#retry * 2, 5000);
		};
	}

	#hello(): ScreenHello {
		const ratio = window.devicePixelRatio || 1;
		return {
			screen_id: this.id,
			agent: navigator.userAgent.slice(0, 300),
			width: Math.max(1, Math.round(window.screen.width * ratio)),
			height: Math.max(1, Math.round(window.screen.height * ratio)),
			refresh_hz: Math.round(1000 / this.#frameMs),
			codecs: this.#codecs,
			preview: this.preview
		};
	}

	#send(message: unknown): void {
		if (this.#socket?.readyState === WebSocket.OPEN) this.#socket.send(JSON.stringify(message));
	}

	#askTime(): void {
		this.#send({ type: 'time-request', sent: Math.round(localMicros()) });
	}

	#message(message: { type: string } & Record<string, unknown>): void {
		const received = localMicros();
		if (message.type === 'time' && typeof message.sent === 'number') {
			this.clock.observe(message.now as number, message.sent, received);
		} else if (message.type === 'config') {
			const before = this.config;
			this.config = message.config as ScreenConfig;
			if (before.layout !== this.config.layout) {
				// What it shows changed: it may need the video it did not download.
				this.dispatch({ type: 'layout-changed' });
				this.#schedule();
			}
		} else if (message.type === 'session') {
			this.#learnTitles(message.session as Session);
			this.dispatch({ type: 'session', session: message.session as Session });
			this.#schedule();
		}
	}

	#status(): ScreenStatus {
		const flags: ScreenStatus['flags'] = [];
		if (!this.connected) flags.push('offline');
		if (this.hidden) flags.push('hidden');
		if (this.degraded) flags.push('degraded');
		if (this.fullscreen) flags.push('fullscreen');
		const video = this.#slots[this.active];
		const dropped = video?.getVideoPlaybackQuality?.().droppedVideoFrames ?? 0;
		return {
			state: this.model.state,
			epoch: this.model.prepared?.epoch ?? null,
			ready: isReady(this.model),
			flags,
			cache: Object.values(this.progress),
			sync: {
				error_ms: p95Ms(this.#errors),
				rtt_ms: this.clock.rttMs,
				drift_ppm: this.clock.driftPpm,
				dropped_frames: dropped
			},
			error: this.model.error
		};
	}

	#report(): void {
		this.#send({ type: 'status', status: this.#status() });
	}

	// Songs: download, keep, read

	#reply(reply: FetchReply): void {
		const request = this.#requests.get(reply.id);
		if (!request) return;
		if (reply.kind === 'progress') {
			request.progress(reply.received);
			return;
		}
		this.#requests.delete(reply.id);
		if (reply.kind === 'failed') request.failed(new Error(reply.error));
		else request.done(reply.inMemory);
	}

	/** Makes sure a blob is here (downloaded and checked); `progress` gets bytes received. */
	async #fetch(sha: string, progress: (n: number) => void = () => {}): Promise<void> {
		if (this.#memory.has(sha) || (await this.#store?.has(sha))) return;
		if (!this.#worker) {
			const { download } = await import('./store');
			const blob = await download(sha, { progress });
			try {
				await this.#store?.put(sha, blob);
			} catch {
				this.#memory.set(sha, blob);
			}
			return;
		}
		const id = this.#nextRequest++;
		await new Promise<void>((done, failed) => {
			this.#requests.set(id, {
				done: (inMemory) => {
					if (inMemory) this.#memory.set(sha, inMemory); // no room in IndexedDB
					done();
				},
				failed,
				progress
			});
			this.#worker?.postMessage({ id, sha } satisfies FetchRequest);
		});
	}

	async #read(sha: string): Promise<Blob> {
		const blob = this.#memory.get(sha) ?? (await this.#store?.get(sha));
		if (!blob) throw new Error(`blob ${sha} is not here`);
		return blob;
	}

	async #manifest(sha: string): Promise<Manifest> {
		const known = this.#manifests.get(sha);
		if (known) return known;
		await this.#fetch(sha);
		const manifest = JSON.parse(await (await this.#read(sha)).text()) as Manifest;
		this.#manifests.set(sha, manifest);
		return manifest;
	}

	#learnTitles(session: Session): void {
		const programs = [session.current, ...session.upcoming].filter((p): p is Program => !!p);
		for (const program of programs) {
			if (this.titles[program.manifest]) continue;
			void this.#manifest(program.manifest)
				.then((m) => {
					this.titles = {
						...this.titles,
						[program.manifest]: { title: m.title, artist: m.artist ?? null }
					};
				})
				.catch(() => {});
		}
	}

	#video(manifest: Manifest): ManifestTrack | null {
		if (!this.#needsVideo()) return null;
		const tall = Math.round(window.screen.height * (window.devicePixelRatio || 1));
		return chooseVideo(manifest, this.#codecs, tall, this.config.video_max_height);
	}

	/** Downloads what this screen needs of a song: its lyrics and the video that fits it. */
	#provision(program: Program): Promise<void> {
		const key = program.manifest;
		let running = this.#provisions.get(key);
		if (!running) {
			running = this.#download(program).finally(() => this.#provisions.delete(key));
			this.#provisions.set(key, running);
		}
		return running;
	}

	async #download(program: Program): Promise<void> {
		const entry = (state: ContentCache['state'], fraction: number, error: string | null = null) => {
			this.progress = {
				...this.progress,
				[program.manifest]: {
					content_id: program.item.content_id,
					manifest: program.manifest,
					state,
					fraction,
					error
				}
			};
		};
		entry('downloading', 0);
		try {
			const manifest = await this.#manifest(program.manifest);
			const wanted = [
				manifest.tracks.find((t) => t.kind === 'lyrics'),
				manifest.tracks.find((t) => t.kind === 'cover'),
				this.#video(manifest)
			].filter((t): t is ManifestTrack => !!t);
			const total = Math.max(
				1,
				wanted.reduce((sum, t) => sum + t.blob.size, 0)
			);
			let done = 0;
			for (const track of wanted) {
				await this.#fetch(track.blob.sha256, (n) => entry('downloading', (done + n) / total));
				done += track.blob.size;
			}
			entry('ready', 1);
		} catch (error) {
			entry('failed', 0, String(error));
			throw error;
		}
	}

	async #provisionCurrent(program: Program): Promise<void> {
		try {
			await this.#provision(program);
			this.dispatch({ type: 'cached', manifest: program.manifest });
		} catch (error) {
			this.dispatch({ type: 'provision-failed', manifest: program.manifest, error: String(error) });
			// It keeps trying while the song is still the one on.
			setTimeout(() => {
				if (
					this.session?.current?.manifest === program.manifest &&
					this.model.state === 'provisioning'
				)
					void this.#provisionCurrent(program);
			}, 5000);
		}
	}

	/** What comes next: downloaded one after another, the first one put in the spare video. */
	async #prefetch(programs: Program[]): Promise<void> {
		for (const program of programs) {
			try {
				await this.#provision(program);
				this.dispatch({ type: 'cached', manifest: program.manifest });
			} catch {
				// tried again when the session names it again
			}
		}
		const next = programs[0];
		if (next) void this.#standby(next).catch(() => {});
		void this.#trim();
	}

	/** Keeps only the blobs of the songs the session names. */
	async #trim(): Promise<void> {
		const session = this.session;
		if (!session || !this.#store) return;
		// eslint-disable-next-line svelte/prefer-svelte-reactivity -- a local list, not state
		const keep = new Set<string>();
		for (const program of [session.current, ...session.upcoming]) {
			if (!program) continue;
			keep.add(program.manifest);
			const manifest = this.#manifests.get(program.manifest);
			manifest?.tracks.forEach((t) => keep.add(t.blob.sha256));
		}
		if (keep.size) await this.#store.keep(keep);
	}

	// The picture

	#songAt(server: number): number {
		const session = this.session;
		if (!session?.anchor || !session.current) return 0;
		return positionAt(session.anchor, server, endOf(session.current));
	}

	/** Server µs when the frame being drawn now is seen: the next refresh plus the TV's delay. */
	#presented(local = localMicros()): number {
		return this.clock.toServer(local + this.#frameMs * 1000 + this.config.display_ms * 1000);
	}

	/** Puts a song's video in one of the two elements; asking twice waits for the same load. */
	#load(slot: number, manifest: string, video: ManifestTrack): Promise<HTMLVideoElement> {
		const loading = this.#loads[slot];
		if (this.#slotSong[slot] === manifest && loading) return loading;
		this.#slotSong[slot] = manifest;
		const load = (async () => {
			const element = this.#slots[slot];
			if (!element) throw new Error('no video element');
			const url = URL.createObjectURL(await this.#read(video.blob.sha256));
			const old = this.#urls[slot];
			if (old) URL.revokeObjectURL(old);
			this.#urls[slot] = url;
			const loaded = once(element, 'loadeddata', 10_000);
			element.src = url;
			await loaded;
			if (element.error) throw new Error('this browser cannot play the video');
			this.#arm(slot); // a new source drops the callbacks the element had
			return element;
		})();
		load.catch(() => {
			if (this.#loads[slot] === load) [this.#loads[slot], this.#slotSong[slot]] = [null, null];
		});
		this.#loads[slot] = load;
		return load;
	}

	/** Looks for a frame and waits until it is on screen (several waiting on one element is fine). */
	async #seek(element: HTMLVideoElement, media: number): Promise<void> {
		const started = performance.now();
		this.#seeking = true;
		try {
			const target = Math.max(0, media);
			if (Math.abs(element.currentTime - target) > 0.001 || element.readyState < 2) {
				const sought = once(element, 'seeked', 3000);
				element.currentTime = target;
				await sought;
			}
			await shown(element);
		} finally {
			this.#seeking = false;
			this.#follower.seeked((performance.now() - started) / 1000);
		}
	}

	async #standby(program: Program): Promise<void> {
		const manifest = await this.#manifest(program.manifest);
		const video = this.#video(manifest);
		if (!video) return;
		const spare = 1 - this.active;
		if (
			this.#slotSong[spare] === program.manifest ||
			this.#slotSong[this.active] === program.manifest
		)
			return;
		const element = await this.#load(spare, program.manifest, video);
		element.pause();
		await this.#seek(element, (program.item.start ?? 0) - video.offset);
	}

	async #prepare(program: Program, epoch: number, anchor: Session['anchor']): Promise<void> {
		if (!anchor) return;
		const token = ++this.#prepareToken;
		try {
			const manifest = await this.#manifest(program.manifest);
			const lyricsTrack = manifest.tracks.find((t) => t.kind === 'lyrics');
			const doc = lyricsTrack
				? docFromTracks(
						manifest,
						JSON.parse(await (await this.#read(lyricsTrack.blob.sha256)).text()) as Lyrics
					)
				: null;
			const video = this.#video(manifest);
			if (video) {
				// The video on if it is this song (a seek), else the spare one (it may hold it already).
				const slot =
					this.#slotSong[this.active] === program.manifest ? this.active : 1 - this.active;
				const element = await this.#load(slot, program.manifest, video);
				element.pause();
				// Playing already (joining half-way): aim where the song will be once the frame is found.
				const now = this.clock.toServer(localMicros());
				const at = movingAt(anchor, now)
					? positionAt(anchor, now + this.#follower.seekLag * 1e6, endOf(program))
					: anchor.position;
				await this.#seek(element, at - video.offset);
				if (token !== this.#prepareToken) return;
				this.#slots[1 - slot]?.pause();
				this.active = slot;
			}
			if (token !== this.#prepareToken) return;
			this.song = { program, manifest, doc, video };
			this.dispatch({ type: 'prepared', manifest: program.manifest, epoch, anchor });
			this.#follow(); // joining a song that already plays: start now, not at the next frame
		} catch (error) {
			if (token === this.#prepareToken) this.dispatch({ type: 'fatal', error: String(error) });
		}
	}

	// Frame by frame

	#tick = (time: number): void => {
		this.#frame = requestAnimationFrame(this.#tick);
		if (this.#lastTick) {
			const delta = time - this.#lastTick;
			if (delta > 4 && delta < 100) this.#frameMs += 0.05 * (delta - this.#frameMs);
		}
		this.#lastTick = time;
		this.#follow(time);
	};

	/**
	 * Starts or stops the picture when the anchor says so. The frame loop calls it, and so does a
	 * timer set for the anchor's instant: a page whose frames are held back (hidden, a slow kiosk)
	 * still starts and stops on time.
	 */
	#follow(time = performance.now()): void {
		const session = this.session;
		if (!session?.anchor || !session.current || !this.clock.ready) return;
		const server = this.#presented();
		const moving =
			movingAt(session.anchor, server) && this.#songAt(server) < endOf(session.current);
		const state = this.model.state;
		const element = this.song?.video ? this.#slots[this.active] : null;
		if ((state === 'waiting' || state === 'paused') && moving) {
			this.dispatch({ type: 'moving' });
			if (element) {
				element.playbackRate = 1;
				void element.play().catch(() => {});
			}
		} else if (state === 'playing' && !moving) {
			this.dispatch({ type: 'stopped' });
			if (element && this.song?.video) {
				element.pause();
				const target = this.#songAt(server) - this.song.video.offset;
				if (Math.abs(element.currentTime - target) > 0.02) element.currentTime = target;
			}
		} else if (state === 'playing' && element && !hasFrameCallbacks(element)) {
			// Without frame callbacks: the media time the element says, once per refresh.
			this.#steer(element, element.currentTime, server);
		} else if (state === 'playing' && element && time - this.#lastFrame > 500) {
			// No frame for half a second while playing: the callbacks were dropped; arm again.
			this.#lastFrame = time;
			this.#arm(this.active);
		}
	}

	/** A timer for the next instant the anchor changes something (a start, a pause). */
	#schedule(): void {
		clearTimeout(this.#wake);
		const anchor = this.session?.anchor;
		if (!anchor || !this.clock.ready) return;
		const lead = this.#frameMs * 1000 + this.config.display_ms * 1000;
		const local = anchor.instant - this.clock.offsetAt(localMicros()) - lead;
		const ms = (local - localMicros()) / 1000;
		if (ms > 0 && ms < 60_000) this.#wake = setTimeout(() => this.#follow(), ms);
	}

	/** Frame callbacks say exactly which frame is shown and when: the servo runs on them. */
	#arm(slot: number): void {
		const element = this.#slots[slot];
		if (!element || !hasFrameCallbacks(element)) return;
		const pending = this.#armed[slot];
		if (pending !== null) element.cancelVideoFrameCallback(pending);
		const onFrame = (now: number, meta: VideoFrameCallbackMetadata) => {
			this.#armed[slot] = element.requestVideoFrameCallback(onFrame);
			if (slot !== this.active || this.model.state !== 'playing') return;
			this.#lastFrame = now;
			const server = this.clock.toServer(
				meta.expectedDisplayTime * 1000 + this.config.display_ms * 1000
			);
			this.#steer(element, meta.mediaTime, server);
		};
		this.#armed[slot] = element.requestVideoFrameCallback(onFrame);
	}

	#steer(element: HTMLVideoElement, mediaTime: number, server: number): void {
		const video = this.song?.video;
		if (!video || this.#seeking) return;
		const span = 1 / (video.video?.fps ?? 30);
		const target = this.#songAt(server) - video.offset;
		this.#errors = [...this.#errors.slice(-ERRORS_KEPT + 1), mediaTime + span / 2 - target];
		const steer = this.#follower.frame(mediaTime, span, target);
		if (steer.kind === 'rate') {
			if (Math.abs(element.playbackRate - steer.rate) > 1e-4) element.playbackRate = steer.rate;
			return;
		}
		const now = performance.now();
		this.#jumps = [...this.#jumps.filter((t) => now - t < JUMP_WINDOW), now];
		this.degraded = this.#jumps.length > JUMPS_TOO_MANY;
		const ahead = target + steer.ahead;
		void this.#seek(element, ahead).then(() => {
			if (this.model.state === 'playing') void element.play().catch(() => {});
		});
	}

	// The page

	#visibility = (): void => {
		this.hidden = document.visibilityState === 'hidden';
		// Hidden, the browser stopped drawing: back, the picture looks for its frame again.
		if (!this.hidden) this.dispatch({ type: 'lost-sync' });
		this.#report();
	};

	#fullscreenChange = (): void => {
		this.fullscreen = document.fullscreenElement !== null;
		this.#report();
	};
}

/** Resolves on the element's next `event` (or its error, or after `ms`: a wait never hangs). */
function once(element: HTMLVideoElement, event: string, ms: number): Promise<void> {
	return new Promise((resolve) => {
		const done = () => {
			clearTimeout(timer);
			element.removeEventListener(event, done);
			element.removeEventListener('error', done);
			resolve();
		};
		const timer = setTimeout(done, ms);
		element.addEventListener(event, done);
		element.addEventListener('error', done);
	});
}

/** Whether the browser says which frame it shows and when (Chromium, Safari, WebKitGTK). */
function hasFrameCallbacks(element: HTMLVideoElement): boolean {
	return typeof element.requestVideoFrameCallback === 'function';
}

/** Resolves once the element has a frame on screen at its current time. */
function shown(element: HTMLVideoElement): Promise<void> {
	return new Promise((resolve) => {
		if (hasFrameCallbacks(element)) element.requestVideoFrameCallback(() => resolve());
		else requestAnimationFrame(() => resolve());
		// A paused element after a seek may never present again in some browsers.
		setTimeout(resolve, 250);
	});
}
