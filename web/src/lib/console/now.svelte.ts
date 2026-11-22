/**
 * The console's own heartbeat: `performance.now()` four times a second, so positions and clocks
 * move between the server's events without each component running its own timer.
 */
class Now {
	value = $state(typeof performance === 'undefined' ? 0 : performance.now());
	private timer: ReturnType<typeof setInterval> | null = null;
	private users = 0;

	/** Starts ticking while at least one component uses it; returns its stop function. */
	use(): () => void {
		this.users += 1;
		this.timer ??= setInterval(() => (this.value = performance.now()), 250);
		return () => {
			this.users -= 1;
			if (this.users === 0 && this.timer) {
				clearInterval(this.timer);
				this.timer = null;
			}
		};
	}
}

export const now = new Now();
