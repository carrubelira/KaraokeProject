/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

/**
 * How `kp-audio` sends the stems to the backend's sound cards.
 */
export interface AudioConfig {
	routing: Routing;
	/**
	 * Per stable device id: how late it really is, beyond what the OS reports.
	 */
	calibration_ms: {
		[k: string]: number;
	};
}
export interface Routing {
	/**
	 * Audio device whose clock rules.
	 */
	master: string | null;
	routes: Route[];
	/**
	 * What happens when an output disappears; default: pause if it is the master, continue otherwise.
	 */
	policies: {
		[k: string]: 'pause' | 'continue';
	};
}
export interface Route {
	track: 'vocals' | 'instrumental';
	/**
	 * An audio device id.
	 */
	output: string;
	/**
	 * None mutes the route.
	 */
	gain_db: number | null;
	delay_ms: number;
}
