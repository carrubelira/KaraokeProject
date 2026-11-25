/** Short notices in a corner: what failed, what was undone. Never a blocking dialog. */
export interface Toast {
	id: number;
	text: string;
	kind: 'info' | 'error';
	action?: { label: string; run: () => void };
}

class Toasts {
	list = $state<Toast[]>([]);
	private next = 1;

	show(text: string, kind: Toast['kind'] = 'info', action?: Toast['action'], ms = 5000): void {
		const toast = { id: this.next++, text, kind, action };
		this.list = [...this.list.slice(-3), toast];
		setTimeout(() => this.dismiss(toast.id), ms);
	}

	dismiss(id: number): void {
		this.list = this.list.filter((t) => t.id !== id);
	}
}

export const toasts = new Toasts();
