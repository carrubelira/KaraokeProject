/**
 * The live line to the server (`/api/events`): a snapshot when it connects, then every change.
 * It reconnects on its own (and reloads the snapshot), and it learns the server's clock.
 */
import { api } from './api';
import { apply, empty, type LiveEvent, type LiveState } from './state';

class Live {
	state = $state<LiveState>(empty());
	connected = $state(false);
	/** Server µs minus local µs. */
	offset = $state(0);
	private socket: WebSocket | null = null;
	private retry = 500;
	private timers: ReturnType<typeof setInterval>[] = [];
	private stopped = true;

	start(): void {
		if (!this.stopped) return;
		this.stopped = false;
		this.connect();
		void this.refreshNodes();
		this.timers.push(setInterval(() => void this.refreshNodes(), 5000));
		this.timers.push(
			setInterval(() => {
				if (this.socket?.readyState === WebSocket.OPEN) {
					this.socket.send(JSON.stringify({ type: 'ping', sent: Date.now() * 1000 }));
				}
			}, 15000)
		);
	}

	stop(): void {
		this.stopped = true;
		this.timers.forEach(clearInterval);
		this.timers = [];
		this.socket?.close();
		this.socket = null;
	}

	private connect(): void {
		const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
		const socket = new WebSocket(`${scheme}://${location.host}/api/events`);
		this.socket = socket;
		socket.onopen = () => {
			this.connected = true;
			this.retry = 500;
			socket.send(JSON.stringify({ type: 'ping', sent: Date.now() * 1000 }));
		};
		socket.onmessage = (message) => {
			const event = JSON.parse(String(message.data)) as LiveEvent;
			if (event.type === 'pong' && event.sent) {
				const local = Date.now() * 1000;
				this.offset = event.now - (event.sent + local) / 2;
			}
			if (event.type === 'snapshot') this.offset = event.now - Date.now() * 1000;
			this.state = apply(this.state, event, performance.now());
			if (event.type === 'node') void this.refreshNodes();
		};
		socket.onclose = () => {
			this.connected = false;
			if (this.stopped) return;
			setTimeout(() => this.connect(), this.retry);
			this.retry = Math.min(this.retry * 2, 10000);
		};
	}

	async refreshNodes(): Promise<void> {
		try {
			const nodes = await api.nodes();
			this.state = { ...this.state, nodes };
		} catch {
			// The events say when the server is back.
		}
	}

	/** A local change shown at once; `revert` undoes it if the server says no. */
	patch(change: (state: LiveState) => LiveState): () => void {
		const before = this.state;
		this.state = change(this.state);
		return () => {
			if (this.state !== before) this.state = before;
		};
	}
}

export const live = new Live();
