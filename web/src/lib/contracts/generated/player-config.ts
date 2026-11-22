/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface PlayerConfig {
	routing: Routing;
	calibration: Calibration;
}
export interface Routing {
	/**
	 * Audio device whose clock rules.
	 */
	master: string | null;
	routes: Route[];
	screens: Screen[];
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
export interface Screen {
	display: string;
	layout: 'video-lyrics' | 'lyrics' | 'video' | 'off';
	theme: string;
}
/**
 * Per stable device id: how late it really is, beyond what the OS reports.
 */
export interface Calibration {
	audio_ms: {
		[k: string]: number;
	};
	display_ms: {
		[k: string]: number;
	};
}
