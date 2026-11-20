import { SvelteSet } from 'svelte/reactivity';
/**
 * Keyboard selection in a list: a cursor (j/k, arrows), marks (x, Shift+j/k to extend, Mod+A),
 * and what the actions apply to: the marked rows, or the cursor's row when nothing is marked.
 */
export class Selection {
	cursor = $state(0);
	marked = $state<Set<string>>(new SvelteSet<string>());
	private anchor: number | null = null;

	constructor(private readonly ids: () => string[]) {}

	get current(): string | undefined {
		return this.ids()[this.cursor];
	}

	/** The rows an action applies to, in list order. */
	get targets(): string[] {
		const ids = this.ids();
		if (this.marked.size) return ids.filter((id) => this.marked.has(id));
		const current = ids[this.cursor];
		return current ? [current] : [];
	}

	clamp(): void {
		const n = this.ids().length;
		this.cursor = Math.max(0, Math.min(this.cursor, n - 1));
	}

	move(step: number): void {
		this.anchor = null;
		this.cursor += step;
		this.clamp();
	}

	extend(step: number): void {
		const ids = this.ids();
		if (this.anchor === null) this.anchor = this.cursor;
		this.cursor += step;
		this.clamp();
		const [from, to] = [Math.min(this.anchor, this.cursor), Math.max(this.anchor, this.cursor)];
		this.marked = new SvelteSet(ids.slice(from, to + 1));
	}

	toggle(): void {
		const id = this.current;
		if (!id) return;
		const next = new SvelteSet(this.marked);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		this.marked = next;
	}

	all(): void {
		this.marked = new SvelteSet(this.ids());
	}

	clear(): void {
		this.marked = new SvelteSet();
		this.anchor = null;
	}

	focusId(id: string): void {
		const index = this.ids().indexOf(id);
		if (index >= 0) this.cursor = index;
	}
}
