<script lang="ts">
	/**
	 * A rotary encoder, like the knobs of a desk: drag up or down, scroll, or use the arrow keys
	 * when it has the focus. It is an ARIA slider; double click puts it back to `reset`.
	 */
	let {
		value,
		min,
		max,
		step,
		reset,
		label,
		text,
		onchange
	}: {
		value: number;
		min: number;
		max: number;
		step: number;
		reset: number;
		label: string;
		text: string;
		onchange: (value: number) => void;
	} = $props();

	let dragging: { y: number; start: number } | null = null;
	let shown = $state<number | null>(null);
	const current = $derived(shown ?? value);
	const fraction = $derived((current - min) / (max - min));
	const angle = $derived(-135 + fraction * 270);

	function clamp(v: number): number {
		return Math.min(max, Math.max(min, Math.round(v / step) * step));
	}

	function set(v: number) {
		const next = clamp(v);
		if (next !== current) {
			shown = next;
			onchange(next);
		}
	}

	function down(event: PointerEvent) {
		dragging = { y: event.clientY, start: current };
		(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
	}

	function move(event: PointerEvent) {
		if (!dragging) return;
		const range = max - min;
		set(dragging.start + ((dragging.y - event.clientY) / 160) * range);
	}

	function up() {
		dragging = null;
		shown = null;
	}

	function wheel(event: WheelEvent) {
		event.preventDefault();
		set(current + (event.deltaY < 0 ? step : -step));
		shown = null;
	}

	function key(event: KeyboardEvent) {
		const moves: Record<string, number> = {
			ArrowUp: step,
			ArrowRight: step,
			ArrowDown: -step,
			ArrowLeft: -step
		};
		if (event.key in moves) {
			event.preventDefault();
			event.stopPropagation();
			set(current + moves[event.key]);
			shown = null;
		}
	}
</script>

<div class="encoder">
	<div
		class="knob"
		role="slider"
		tabindex="0"
		aria-label={label}
		aria-valuemin={min}
		aria-valuemax={max}
		aria-valuenow={current}
		aria-valuetext={text}
		onpointerdown={down}
		onpointermove={move}
		onpointerup={up}
		onpointercancel={up}
		onwheel={wheel}
		onkeydown={key}
		ondblclick={() => set(reset)}
		style:--angle={`${angle}deg`}
		style:--fill={fraction}
	>
		<span class="dial" aria-hidden="true"></span>
	</div>
	<div class="read">
		<span class="label">{label}</span>
		<span class="mono value">{text}</span>
	</div>
</div>

<style>
	.encoder {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.knob {
		position: relative;
		width: 44px;
		height: 44px;
		border-radius: 50%;
		background: conic-gradient(
			from -135deg,
			var(--info) calc(var(--fill) * 270deg),
			rgb(150 175 205 / 0.12) 0 270deg,
			transparent 0
		);
		cursor: ns-resize;
		touch-action: none;
		flex: none;
	}
	.knob::before {
		content: '';
		position: absolute;
		inset: 4px;
		border-radius: 50%;
		background: radial-gradient(circle at 35% 30%, #222a35, #0b0f14 70%);
		box-shadow:
			inset 0 1px 0 rgb(255 255 255 / 0.08),
			0 4px 10px rgb(0 0 0 / 0.6);
	}
	.dial {
		position: absolute;
		left: 50%;
		top: 8px;
		width: 2px;
		height: 11px;
		margin-left: -1px;
		background: var(--text);
		border-radius: 1px;
		transform-origin: 50% 14px;
		transform: rotate(var(--angle));
		box-shadow: 0 0 6px rgb(255 255 255 / 0.5);
	}
	.read {
		display: flex;
		flex-direction: column;
		gap: 4px;
		min-width: 64px;
	}
	.value {
		font-size: 13px;
	}
</style>
