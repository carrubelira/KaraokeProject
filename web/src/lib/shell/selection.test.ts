import { describe, expect, it } from 'vitest';
import { Selection } from './selection.svelte';

describe('keyboard selection', () => {
	it('moves, marks, extends and gives the targets in list order', () => {
		const ids = ['a', 'b', 'c', 'd'];
		const s = new Selection(() => ids);
		expect(s.targets).toEqual(['a']);
		s.move(2);
		expect(s.current).toBe('c');
		s.move(10);
		expect(s.current).toBe('d');
		s.extend(-2);
		expect(s.targets).toEqual(['b', 'c', 'd']);
		s.clear();
		s.toggle();
		s.move(-3);
		s.toggle();
		expect(s.targets).toEqual(['a', 'b']);
		s.all();
		expect(s.targets).toEqual(ids);
	});
});
