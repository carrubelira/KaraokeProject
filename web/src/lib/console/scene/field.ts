/**
 * The signal field behind the console (Three.js): the system as it is, at a glance.
 *
 * - The floor is a sheet of points that breathes with the work in flight: waves start at every
 *   busy worker and at the screen on air.
 * - Each worker is a core of particles on the left; its spin and size follow its GPU, it turns
 *   red when one of its tasks failed, and particles stream from it to the hub while it works.
 * - Each screen is a core on the right: red and pulsing on air, green when a song is cued, amber
 *   when something on it is broken, grey when it is off; the hub feeds it while it plays.
 *
 * Purely decorative: every state it shows is also written in the interface.
 */
import * as THREE from 'three';
import type { Signals } from './signals';

// The colours below are the console's own sRGB tokens, drawn as they are by raw shaders.
THREE.ColorManagement.enabled = false;

export type Motion = 'full' | 'calm' | 'off';

const COLOURS = {
	idle: new THREE.Color('#3a4656'),
	info: new THREE.Color('#3cc8ff'),
	onair: new THREE.Color('#ff3a46'),
	cue: new THREE.Color('#24e38f'),
	warn: new THREE.Color('#ffb020'),
	floor: new THREE.Color('#5f7ea3')
};
const MAX_SOURCES = 8;
const FLOW_PARTICLES = 900;
const CORE_POINTS = 520;

const floorVertex = /* glsl */ `
uniform float uTime;
uniform float uEnergy;
uniform vec4 uSources[${MAX_SOURCES}];
uniform vec3 uSourceColours[${MAX_SOURCES}];
varying vec3 vColour;
varying float vAlpha;
uniform vec3 uBase;

void main() {
	vec3 p = position;
	float lift = 0.0;
	vec3 tint = vec3(0.0);
	for (int i = 0; i < ${MAX_SOURCES}; i++) {
		vec4 s = uSources[i];
		if (s.w <= 0.0) continue;
		float d = distance(p.xz, s.xy);
		float wave = sin(d * 1.6 - uTime * (1.2 + s.w * 1.8)) * exp(-d * 0.22) * s.w;
		lift += wave * 0.55;
		tint += uSourceColours[i] * max(0.0, wave) * 1.4;
	}
	float swell = sin(p.x * 0.18 + uTime * 0.25) * cos(p.z * 0.21 - uTime * 0.2) * (0.25 + uEnergy * 0.5);
	p.y += lift + swell;
	vec4 view = modelViewMatrix * vec4(p, 1.0);
	gl_Position = projectionMatrix * view;
	gl_PointSize = (2.6 + max(0.0, lift) * 3.0) * (34.0 / -view.z);
	vColour = uBase * (0.5 + uEnergy * 0.5) + tint;
	// Fades with distance (smoothstep needs its edges in order).
	vAlpha = clamp(0.35 + abs(lift) * 0.9, 0.0, 1.0) * (1.0 - smoothstep(14.0, 52.0, -view.z));
}`;

const pointFragment = /* glsl */ `
varying vec3 vColour;
varying float vAlpha;
void main() {
	vec2 c = gl_PointCoord - 0.5;
	float r = length(c);
	if (r > 0.5) discard;
	gl_FragColor = vec4(vColour, vAlpha * smoothstep(0.5, 0.0, r));
}`;

const coreVertex = /* glsl */ `
uniform float uTime;
uniform float uSpin;
uniform float uPulse;
uniform float uScale;
uniform vec3 uColour;
attribute float aSeed;
varying vec3 vColour;
varying float vAlpha;
void main() {
	float a = uTime * uSpin + aSeed * 6.2831;
	vec3 p = position;
	float c = cos(a * 0.3), s = sin(a * 0.3);
	p = vec3(p.x * c - p.z * s, p.y, p.x * s + p.z * c);
	float breath = 1.0 + sin(uTime * 3.0 + aSeed * 12.0) * 0.06 + uPulse * 0.22;
	p *= uScale * breath;
	vec4 view = modelViewMatrix * vec4(p, 1.0);
	gl_Position = projectionMatrix * view;
	gl_PointSize = (3.2 + uPulse * 3.0) * (30.0 / -view.z);
	vColour = uColour;
	vAlpha = 0.55 + 0.45 * uPulse;
}`;

const flowVertex = /* glsl */ `
attribute vec3 aColour;
attribute float aAlpha;
varying vec3 vColour;
varying float vAlpha;
void main() {
	vec4 view = modelViewMatrix * vec4(position, 1.0);
	gl_Position = projectionMatrix * view;
	gl_PointSize = 4.0 * (30.0 / -view.z);
	vColour = aColour;
	vAlpha = aAlpha;
}`;

interface Core {
	id: string;
	points: THREE.Points;
	material: THREE.ShaderMaterial;
	position: THREE.Vector3;
	colour: THREE.Color;
	target: THREE.Color;
	scale: number;
	spin: number;
	pulse: number;
}

interface Stream {
	from: THREE.Vector3;
	to: THREE.Vector3;
	colour: THREE.Color;
	rate: number;
}

function sphere(count: number): THREE.BufferGeometry {
	const geometry = new THREE.BufferGeometry();
	const positions = new Float32Array(count * 3);
	const seeds = new Float32Array(count);
	for (let i = 0; i < count; i++) {
		// Fibonacci sphere, with some points thrown into an orbit ring.
		const ring = i % 5 === 0;
		const t = i / count;
		const phi = Math.acos(1 - 2 * t);
		const theta = Math.PI * (1 + Math.sqrt(5)) * i;
		const r = ring ? 1.7 + Math.random() * 0.15 : 1;
		positions[i * 3] = ring ? Math.cos(theta) * r : Math.sin(phi) * Math.cos(theta);
		positions[i * 3 + 1] = ring ? (Math.random() - 0.5) * 0.06 : Math.cos(phi);
		positions[i * 3 + 2] = ring ? Math.sin(theta) * r : Math.sin(phi) * Math.sin(theta);
		seeds[i] = Math.random();
	}
	geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
	geometry.setAttribute('aSeed', new THREE.BufferAttribute(seeds, 1));
	return geometry;
}

export class Field {
	private renderer: THREE.WebGLRenderer;
	private scene = new THREE.Scene();
	private camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200);
	private floor: THREE.ShaderMaterial;
	private cores = new Map<string, Core>();
	private hub: Core;
	private flow: THREE.BufferGeometry;
	private flowPhase = new Float32Array(FLOW_PARTICLES);
	private streams: Stream[] = [];
	private clock = new THREE.Clock();
	private frame = 0;
	private signals: Signals | null = null;
	private energy = 0;
	private disposed = false;

	constructor(
		private canvas: HTMLCanvasElement,
		private motion: Motion
	) {
		this.renderer = new THREE.WebGLRenderer({
			canvas,
			antialias: false,
			alpha: true,
			powerPreference: 'low-power'
		});
		this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
		this.scene.fog = new THREE.FogExp2(0x030507, 0.028);
		this.camera.position.set(0, 9, 26);
		this.camera.lookAt(0, 0, 0);

		const cols = 150;
		const rows = 80;
		const positions = new Float32Array(cols * rows * 3);
		for (let i = 0; i < cols; i++) {
			for (let j = 0; j < rows; j++) {
				const k = (i * rows + j) * 3;
				positions[k] = (i / (cols - 1) - 0.5) * 64;
				positions[k + 1] = -3.2;
				positions[k + 2] = (j / (rows - 1) - 0.5) * 40 - 4;
			}
		}
		const floorGeometry = new THREE.BufferGeometry();
		floorGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
		this.floor = new THREE.ShaderMaterial({
			vertexShader: floorVertex,
			fragmentShader: pointFragment,
			transparent: true,
			depthWrite: false,
			blending: THREE.AdditiveBlending,
			uniforms: {
				uTime: { value: 0 },
				uEnergy: { value: 0 },
				uBase: { value: COLOURS.floor.clone() },
				uSources: { value: Array.from({ length: MAX_SOURCES }, () => new THREE.Vector4()) },
				uSourceColours: { value: Array.from({ length: MAX_SOURCES }, () => new THREE.Color()) }
			}
		});
		this.scene.add(new THREE.Points(floorGeometry, this.floor));

		this.hub = this.makeCore('hub', new THREE.Vector3(0, 0.6, -2), COLOURS.info, 1.1);

		this.flow = new THREE.BufferGeometry();
		this.flow.setAttribute(
			'position',
			new THREE.BufferAttribute(new Float32Array(FLOW_PARTICLES * 3), 3)
		);
		this.flow.setAttribute(
			'aColour',
			new THREE.BufferAttribute(new Float32Array(FLOW_PARTICLES * 3), 3)
		);
		this.flow.setAttribute(
			'aAlpha',
			new THREE.BufferAttribute(new Float32Array(FLOW_PARTICLES), 1)
		);
		for (let i = 0; i < FLOW_PARTICLES; i++) this.flowPhase[i] = Math.random();
		this.scene.add(
			new THREE.Points(
				this.flow,
				new THREE.ShaderMaterial({
					vertexShader: flowVertex,
					fragmentShader: pointFragment,
					transparent: true,
					depthWrite: false,
					blending: THREE.AdditiveBlending
				})
			)
		);
		this.resize();
		document.addEventListener('visibilitychange', this.onVisibility);
		this.loop();
	}

	private makeCore(id: string, position: THREE.Vector3, colour: THREE.Color, scale: number): Core {
		const material = new THREE.ShaderMaterial({
			vertexShader: coreVertex,
			fragmentShader: pointFragment,
			transparent: true,
			depthWrite: false,
			blending: THREE.AdditiveBlending,
			uniforms: {
				uTime: { value: 0 },
				uSpin: { value: 0.4 },
				uPulse: { value: 0 },
				uScale: { value: scale },
				uColour: { value: colour.clone() }
			}
		});
		const points = new THREE.Points(sphere(CORE_POINTS), material);
		points.position.copy(position);
		this.scene.add(points);
		const core = {
			id,
			points,
			material,
			position,
			colour: colour.clone(),
			target: colour.clone(),
			scale,
			spin: 0.4,
			pulse: 0
		};
		return core;
	}

	setMotion(motion: Motion): void {
		this.motion = motion;
		if (motion !== 'off') this.loop();
	}

	update(signals: Signals): void {
		this.signals = signals;
		this.layout(signals);
		if (this.motion === 'off') this.render(0);
	}

	/** Workers on an arc to the left, screens on an arc to the right; cores come and go. */
	private layout(signals: Signals): void {
		const wanted = new Set<string>();
		const place = (index: number, count: number, side: -1 | 1) => {
			const spread = Math.min(1.1, 0.42 * Math.max(0, count - 1));
			const angle = count > 1 ? -spread / 2 + (spread * index) / (count - 1) : 0;
			return new THREE.Vector3(
				side * (11 + Math.cos(angle) * 2),
				0.8 + Math.sin(angle) * 5.5,
				-3 - Math.abs(angle) * 3
			);
		};
		signals.workers.forEach((w, i) => {
			const key = `w:${w.id}`;
			wanted.add(key);
			const at = place(i, signals.workers.length, -1);
			const core = this.cores.get(key) ?? this.makeCore(key, at, COLOURS.idle, 0.8);
			this.cores.set(key, core);
			core.position.copy(at);
			core.target = !w.online
				? COLOURS.idle
				: w.failing
					? COLOURS.onair
					: w.tasks
						? COLOURS.info
						: COLOURS.cue;
			core.scale = 0.7 + w.memory * 0.5 + (w.tasks ? 0.15 : 0);
			core.spin = w.online ? 0.3 + w.load * 2.4 : 0.05;
			core.pulse = w.tasks ? 0.35 + w.load * 0.65 : 0;
		});
		signals.screens.forEach((s, i) => {
			const key = `s:${s.id}`;
			wanted.add(key);
			const at = place(i, signals.screens.length, 1);
			const core = this.cores.get(key) ?? this.makeCore(key, at, COLOURS.idle, 0.8);
			this.cores.set(key, core);
			core.position.copy(at);
			const playing = s.state === 'playing';
			core.target = !s.online
				? COLOURS.idle
				: s.alarm
					? COLOURS.warn
					: playing
						? COLOURS.onair
						: s.state === 'idle'
							? COLOURS.idle
							: COLOURS.cue;
			core.scale = (s.selected ? 1 : 0.75) * (playing ? 1.05 : 0.9);
			core.spin = playing ? 1.2 : 0.25;
			core.pulse = playing ? 1 : s.state === 'loading' || s.state === 'waiting' ? 0.5 : 0;
		});
		for (const [key, core] of this.cores) {
			if (wanted.has(key)) continue;
			this.scene.remove(core.points);
			core.points.geometry.dispose();
			core.material.dispose();
			this.cores.delete(key);
		}
		this.hub.target = !signals.connected
			? COLOURS.onair
			: signals.review
				? COLOURS.warn
				: COLOURS.info;
		this.streams = [];
		for (const w of signals.workers) {
			if (!w.tasks || !w.online) continue;
			const core = this.cores.get(`w:${w.id}`);
			if (core)
				this.streams.push({
					from: core.position,
					to: this.hub.position,
					colour: w.failing ? COLOURS.onair : COLOURS.info,
					rate: 0.3 + w.load
				});
		}
		for (const s of signals.screens) {
			if (s.state !== 'playing' || !s.online) continue;
			const core = this.cores.get(`s:${s.id}`);
			if (core)
				this.streams.push({
					from: this.hub.position,
					to: core.position,
					colour: COLOURS.onair,
					rate: 0.8
				});
		}
	}

	private onVisibility = () => {
		if (!document.hidden) this.loop();
	};

	private loop = () => {
		cancelAnimationFrame(this.frame);
		if (this.disposed || document.hidden || this.motion === 'off') return;
		this.frame = requestAnimationFrame(this.loop);
		this.render(this.clock.getDelta());
	};

	resize(): void {
		const { clientWidth: width, clientHeight: height } = this.canvas;
		if (!width || !height) return;
		this.renderer.setSize(width, height, false);
		this.camera.aspect = width / height;
		this.camera.fov = width < 860 ? 58 : 42;
		this.camera.updateProjectionMatrix();
		if (this.motion === 'off') this.render(0);
	}

	private render(delta: number): void {
		const speed = this.motion === 'calm' ? 0.35 : 1;
		const time = (this.floor.uniforms.uTime.value as number) + delta * speed;
		const signals = this.signals;
		const busy = signals
			? signals.workers.reduce((sum, w) => sum + (w.tasks ? 0.4 + w.load * 0.6 : 0), 0)
			: 0;
		const onAir = signals?.screens.some((s) => s.state === 'playing') ? 1 : 0;
		this.energy += (Math.min(1, busy * 0.6 + onAir * 0.5) - this.energy) * Math.min(1, delta * 1.5);
		this.floor.uniforms.uTime.value = time;
		this.floor.uniforms.uEnergy.value = this.energy;

		const sources = this.floor.uniforms.uSources.value as THREE.Vector4[];
		const tints = this.floor.uniforms.uSourceColours.value as THREE.Color[];
		let n = 0;
		const add = (core: Core, strength: number) => {
			if (n >= MAX_SOURCES || strength <= 0) return;
			sources[n].set(core.points.position.x, core.points.position.z, 0, strength);
			tints[n].copy(core.colour);
			n++;
		};
		add(this.hub, 0.25 + this.energy * 0.4);
		for (const core of this.cores.values()) add(core, core.pulse);
		for (; n < MAX_SOURCES; n++) sources[n].w = 0;

		for (const core of [this.hub, ...this.cores.values()]) {
			core.colour.lerp(core.target, Math.min(1, delta * 3 + (this.motion === 'off' ? 1 : 0)));
			core.points.position.lerp(core.position, this.motion === 'off' ? 1 : Math.min(1, delta * 2));
			const u = core.material.uniforms;
			u.uTime.value = time;
			u.uSpin.value += (core.spin - (u.uSpin.value as number)) * Math.min(1, delta * 2);
			u.uPulse.value += (core.pulse - (u.uPulse.value as number)) * Math.min(1, delta * 2);
			u.uScale.value += (core.scale - (u.uScale.value as number)) * Math.min(1, delta * 2);
			(u.uColour.value as THREE.Color).copy(core.colour);
		}

		this.moveFlow(delta * speed);
		const drift = this.motion === 'full' ? 1 : 0.3;
		this.camera.position.x = Math.sin(time * 0.05) * 2.2 * drift;
		this.camera.position.y = 9 + Math.sin(time * 0.07) * 0.6 * drift;
		this.camera.lookAt(0, 0, -2);
		this.renderer.render(this.scene, this.camera);
	}

	private moveFlow(delta: number): void {
		const positions = this.flow.getAttribute('position') as THREE.BufferAttribute;
		const colours = this.flow.getAttribute('aColour') as THREE.BufferAttribute;
		const alphas = this.flow.getAttribute('aAlpha') as THREE.BufferAttribute;
		const point = new THREE.Vector3();
		const control = new THREE.Vector3();
		for (let i = 0; i < FLOW_PARTICLES; i++) {
			const stream = this.streams.length ? this.streams[i % this.streams.length] : null;
			if (!stream) {
				alphas.setX(i, 0);
				continue;
			}
			this.flowPhase[i] = (this.flowPhase[i] + delta * 0.22 * stream.rate) % 1;
			const t = this.flowPhase[i];
			control.copy(stream.from).add(stream.to).multiplyScalar(0.5);
			control.y += 3.5 + ((i * 7919) % 100) / 60;
			control.z += (((i * 104729) % 100) / 100 - 0.5) * 3;
			// A quadratic Bézier from the source, over the floor, to the target.
			point
				.copy(stream.from)
				.multiplyScalar((1 - t) * (1 - t))
				.addScaledVector(control, 2 * (1 - t) * t)
				.addScaledVector(stream.to, t * t);
			positions.setXYZ(i, point.x, point.y, point.z);
			colours.setXYZ(i, stream.colour.r, stream.colour.g, stream.colour.b);
			alphas.setX(i, Math.sin(t * Math.PI) * 0.85);
		}
		positions.needsUpdate = true;
		colours.needsUpdate = true;
		alphas.needsUpdate = true;
	}

	dispose(): void {
		this.disposed = true;
		cancelAnimationFrame(this.frame);
		document.removeEventListener('visibilitychange', this.onVisibility);
		this.scene.traverse((object) => {
			if (object instanceof THREE.Points) {
				const points = object as THREE.Points<THREE.BufferGeometry, THREE.Material>;
				points.geometry.dispose();
				points.material.dispose();
			}
		});
		this.renderer.dispose();
	}
}
