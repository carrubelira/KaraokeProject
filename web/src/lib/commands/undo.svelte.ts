/**
 * Global undo and redo (Mod+Z, Mod+Shift+Z) for what an operator does to the queue and the
 * playlists. Every action knows how to undo itself against the server (a new write, so it goes
 * through the same optimistic versioning as any other change).
 */

export interface Undoable {
	label: string;
	undo: () => Promise<void>;
	redo: () => Promise<void>;
}

const LIMIT = 100;

class UndoStack {
	past = $state<Undoable[]>([]);
	future = $state<Undoable[]>([]);
	busy = $state(false);

	push(action: Undoable): void {
		this.past = [...this.past.slice(-LIMIT + 1), action];
		this.future = [];
	}

	get canUndo(): boolean {
		return this.past.length > 0 && !this.busy;
	}

	get canRedo(): boolean {
		return this.future.length > 0 && !this.busy;
	}

	async undo(): Promise<Undoable | null> {
		const action = this.past.at(-1);
		if (!action || this.busy) return null;
		this.busy = true;
		try {
			await action.undo();
			this.past = this.past.slice(0, -1);
			this.future = [...this.future, action];
			return action;
		} finally {
			this.busy = false;
		}
	}

	async redo(): Promise<Undoable | null> {
		const action = this.future.at(-1);
		if (!action || this.busy) return null;
		this.busy = true;
		try {
			await action.redo();
			this.future = this.future.slice(0, -1);
			this.past = [...this.past, action];
			return action;
		} finally {
			this.busy = false;
		}
	}

	clear(): void {
		this.past = [];
		this.future = [];
	}
}

export const history = new UndoStack();
export { UndoStack };
