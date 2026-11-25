/**
 * The live line to the server (`/api/events`): a snapshot when it connects, then every change.
 *
 * Nothing it shows may go stale: when an event is missing (its sequence number skips one) or the
 * server stops answering pings, the line is dropped and opened again, which brings a fresh
 * snapshot. It also learns the server's clock.
 */
import { apply, empty, missed, type LiveEvent, type LiveState } from './state';

const PING_EVERY = 10_000;
/** No answer for this long: the line is dead even if the socket has not noticed. */
const SILENCE = 25_000;

class Live {
	state = $state<LiveState>(empty());
	connected = $state(false);
	/** Server µs minus local µs. */
	offset = $state(0);
	/** Round trip of the last ping, in ms. */
	latency = $state<number | null>(null);
	private socket: WebSocket | null = null;
	private retry = 500;
	private timer: ReturnType<typeof setInterval> | null = null;
	private heard = 0;
	private stopped = true;

	start(): void {
		if (!this.stopped) return;
		this.stopped = false;
		this.connect();
		this.timer = setInterval(() => this.ping(), PING_EVERY);
	}

	stop(): void {
		this.stopped = true;
		if (this.timer) clearInterval(this.timer);
		this.timer = null;
		this.socket?.close();
		this.socket = null;
	}

	private ping(): void {
		const socket = this.socket;
		if (socket?.readyState !== WebSocket.OPEN) return;
		if (performance.now() - this.heard > SILENCE) {
			socket.close(4000, 'silent');
			return;
		}
		socket.send(JSON.stringify({ type: 'ping', sent: Date.now() * 1000 }));
	}

	private connect(): void {
		const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
		const socket = new WebSocket(`${scheme}://${location.host}/api/events`);
		this.socket = socket;
		socket.onopen = () => {
			this.connected = true;
			this.retry = 500;
			this.heard = performance.now();
			this.ping();
		};
		socket.onmessage = (message) => {
			this.heard = performance.now();
			const event = JSON.parse(String(message.data)) as LiveEvent;
			if (missed(this.state, event)) {
				// Something was lost on the way: start again from a fresh snapshot.
				socket.close(4000, 'gap');
				return;
			}
			if (event.type === 'pong' && event.sent) {
				const local = Date.now() * 1000;
				this.offset = event.now - (event.sent + local) / 2;
				this.latency = (local - event.sent) / 1000;
			}
			if (event.type === 'snapshot') this.offset = event.now - Date.now() * 1000;
			this.state = apply(this.state, event);
		};
		socket.onclose = () => {
			if (this.socket !== socket) return;
			this.connected = false;
			this.state = { ...this.state, seq: 0 };
			if (this.stopped) return;
			setTimeout(() => this.connect(), this.retry);
			this.retry = Math.min(this.retry * 2, 10000);
		};
	}

	/** A local change shown at once; `revert` undoes it if the server says no. */
	patch(change: (state: LiveState) => LiveState): () => void {
		const before = this.state;
		this.state = change(this.state);
		return () => {
			if (this.state !== before) this.state = { ...before, seq: this.state.seq };
		};
	}

	/** The server's clock now, in µs (the one the stage's anchors are on). */
	serverMicros(): number {
		return Date.now() * 1000 + this.offset;
	}
}

export const live = new Live();
