/* Hero WebGL background (Three.js r160 ES module).
   Renders animated light-trail tubes flowing along a bending floor
   into the #webgl-canvas of the hero section, with bloom, SMAA and a
   custom foreground-blur post-processing chain. */

import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
let scene, camera, renderer, composer, bloomPass, blurPass, smaaPass, outputPass;
let clock = new THREE.Clock();
let globalTime = 0;
let floorMesh;
const trailObjects = [];
const trailMaterials = [];
let canvas, container;
const config = {
  dpr: Math.min(window.devicePixelRatio, 1.5),
  exposure: 3.6505,
  brightness: 4.0131,
  bloomStrength: 0.2025,
  bloomRadius: 0.294,
  bloomThreshold: 0.0,
  speedMultiplier: 0.1,
  linesCount: 100,
  dotDensity: 70,
  dotSize: 0.25,
  dotSpeed: 1.5,
  blurStrength: 3.5,
  arcRadius: 10.0,
  bendStartZ: -150.0,
  floorLength: 132.75,
  wallHeight: 200.0,
  color0: '#080c14',
  color1: '#0ea5e9',
  color2: '#22d3ee',
  color3: '#ffffff',
  color4: '#0b1220'
};
class CycCurve extends THREE.Curve {
  constructor(x, zStart, zBend, radius, yEnd) {
    super();
    this.x = x;
    this.zStart = zStart;
    this.zBend = zBend;
    this.radius = radius;
    this.yEnd = yEnd;
    this.L_flat = Math.abs(zStart - (zBend + radius));
    this.L_arc = (Math.PI * radius) * 0.5;
    this.L_up = Math.max(0.1, yEnd - radius);
    this.totalLength = this.L_flat + this.L_arc + this.L_up;
  }
  getPoint(t, optionalTarget = new THREE.Vector3()) {
    const d = t * this.totalLength;
    let py = 0, pz = 0;
    if (d <= this.L_flat) {
      pz = this.zStart - d;
    } else if (d <= this.L_flat + this.L_arc) {
      const norm = (d - this.L_flat) / this.L_arc;
      const eased = norm * norm * (3.0 - 2.0 * norm);
      const angle = (norm * 0.4 + eased * 0.6) * (Math.PI * 0.5);
      py = this.radius * (1.0 - Math.cos(angle));
      pz = (this.zBend + this.radius) - Math.sin(angle) * this.radius;
    } else {
      py = this.radius + (d - (this.L_flat + this.L_arc));
      pz = this.zBend;
    }
    return optionalTarget.set(this.x, py, pz);
  }
}
init();
animate();
function getWidth() { return container.clientWidth; }
function getHeight() { return container.clientHeight; }
function init() {
  canvas = document.querySelector('#webgl-canvas');
  if (!canvas) return;
  container = canvas.parentElement;
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x000000);
  camera = new THREE.PerspectiveCamera(55, getWidth() / getHeight(), 1, 2000);
  camera.position.set(0, 20, 140);
  renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, powerPreference: "high-performance" });
  renderer.setSize(getWidth(), getHeight());
  renderer.setPixelRatio(config.dpr);
  renderer.toneMapping = THREE.LinearToneMapping;
  renderer.toneMappingExposure = config.exposure;
  camera.lookAt(0, 20, -50);
  const renderTarget = new THREE.WebGLRenderTarget(
    getWidth() * config.dpr,
    getHeight() * config.dpr,
    { type: THREE.HalfFloatType, format: THREE.RGBAFormat }
  );
  const renderScene = new RenderPass(scene, camera);
  smaaPass = new SMAAPass( getWidth() * config.dpr, getHeight() * config.dpr );
  bloomPass = new UnrealBloomPass(new THREE.Vector2(getWidth(), getHeight()), config.bloomStrength, config.bloomRadius, config.bloomThreshold);
  const foregroundBlurShader = {
    uniforms: {
      'tDiffuse': { value: null },
      'resolution': { value: new THREE.Vector2(getWidth() * config.dpr, getHeight() * config.dpr) },
      'blurStrength': { value: config.blurStrength }
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform sampler2D tDiffuse;
      uniform vec2 resolution;
      uniform float blurStrength;
      varying vec2 vUv;
      void main() {
        float mask = 1.0 - smoothstep(0.0, 0.35, vUv.y);
        float radius = mask * blurStrength;
        if (radius < 0.1) {
          gl_FragColor = texture2D(tDiffuse, vUv);
        } else {
          vec4 color = vec4(0.0);
          float total = 0.0;
          const float GA = 2.3999632;
          for (int i = 0; i < 32; i++) {
            float f = float(i);
            float r = sqrt(f) * radius;
            float theta = f * GA;
            vec2 offset = vec2(cos(theta), sin(theta)) * (r / resolution);
            color += texture2D(tDiffuse, vUv + offset);
            total += 1.0;
          }
          gl_FragColor = color / total;
        }
      }
    `
  };
  blurPass = new ShaderPass(foregroundBlurShader);
  outputPass = new OutputPass();
  composer = new EffectComposer(renderer, renderTarget);
  composer.setPixelRatio(config.dpr);
  composer.addPass(renderScene);
  composer.addPass(smaaPass);
  composer.addPass(bloomPass);
  composer.addPass(blurPass);
  composer.addPass(outputPass);
  createFloor();
  generateTrails();
  updateGeometries();
  window.addEventListener('resize', onWindowResize);
}
function createFloor() {
  const floorMat = new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.85, depthWrite: false, side: THREE.DoubleSide });
  floorMesh = new THREE.Mesh(new THREE.BufferGeometry(), floorMat);
  floorMesh.position.set(0, -0.5, -0.5);
  floorMesh.renderOrder = 1;
  scene.add(floorMesh);
}
function generateTrails() {
  const group = new THREE.Group();
  scene.add(group);
  const vertexShader = `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    void main() {
      vUv = uv;
      vNormal = normalMatrix * normal;
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      vViewPosition = -mvPosition.xyz;
      gl_Position = projectionMatrix * mvPosition;
    }
  `;
  const fragmentShader = `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    uniform float uTime;
    uniform vec3 uColor;
    uniform float uSpeed;
    uniform float uOffset;
    uniform float uTailLength;
    uniform float uIntensityMultiplier;
    uniform float uBendUv;
    uniform float uIsReflection;
    uniform float uDotDensity;
    uniform float uDotSize;
    uniform float uDotSpeed;
    uniform float uBrightness;
    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
    }
    void main() {
      float t = fract(uTime * uSpeed + uOffset);
      float dist = fract(t - vUv.x + 1.0);
      float baseAlpha = smoothstep(uTailLength, 0.0, dist);
      baseAlpha = pow(max(0.0, baseAlpha), 1.2);
      vec3 viewDir = normalize(vViewPosition);
      float fresnel = abs(dot(normalize(vNormal), viewDir));
      float edgeSoftness = smoothstep(0.0, 0.02, fresnel);
      baseAlpha *= edgeSoftness;
      float core = pow(max(0.0, baseAlpha), 3.0) * 1.5;
      float movingUV = vUv.x - (uTime * uSpeed * uDotSpeed) - uOffset;
      float signalPos = movingUV * uDotDensity;
      float dotId = floor(signalPos);
      float dotLocal = fract(signalPos);
      float distToCenter = length(vec2((dotLocal - 0.5) * 2.0, (fract(vUv.y + 0.5) - 0.5) * 6.0));
      float dotShape = 1.0 - smoothstep(0.0, max(0.001, uDotSize), distToCenter);
      float dotFinal = dotShape * step(0.6, hash(vec2(dotId, uOffset))) * (sin(uTime * 4.0 + hash(vec2(dotId)) * 6.28) * 0.3 + 0.7) * baseAlpha;
      if (uIsReflection > 0.5) {
        float refFade = 1.0 - smoothstep(uBendUv - 0.015, uBendUv, vUv.x);
        baseAlpha *= refFade;
        core *= refFade;
        dotFinal *= refFade * 0.1;
        baseAlpha = pow(max(0.0, baseAlpha), 0.5) * (0.7 + hash(vUv * 300.0 + uTime * 0.05) * 0.3);
        core *= 0.3;
      }
      vec3 trailColor = uColor * (baseAlpha + core * 1.5) * uIntensityMultiplier * uBrightness;
      vec3 rgb = trailColor / max(1.0 - clamp(dotFinal * 1.8, 0.0, 0.95), 0.001) + uColor * dotFinal * 2.5 * uIntensityMultiplier * uBrightness;
      gl_FragColor = vec4(rgb, (baseAlpha + dotFinal) * uIntensityMultiplier);
    }
  `;
  for (let i = 0; i < config.linesCount; i++) {
    const normIdx = (i / (config.linesCount - 1)) * 2 - 1;
    const linearPos = normIdx;
    const expPos = Math.sign(normIdx) * Math.pow(Math.abs(normIdx), 1.2);
    let startX = (linearPos * 0.5 + expPos * 0.5) * 80;
    startX += (Math.random() - 0.5) * 2.0;
    const thickness = Math.random() * 0.2 + 0.1;
    const colorIdx = Math.floor(Math.random() * 5);
    const uniforms = {
      uTime: { value: 0 },
      uColor: { value: new THREE.Color(config[`color${colorIdx}`]) },
      uColorIndex: { value: colorIdx },
      uSpeed: { value: Math.random() * 0.5 + 0.2 },
      uOffset: { value: Math.random() },
      uTailLength: { value: Math.random() * 0.4 + 0.3 },
      uIntensityMultiplier: { value: 1.0 },
      uBendUv: { value: 0.0 },
      uIsReflection: { value: 0.0 },
      uDotDensity: { value: config.dotDensity },
      uDotSize: { value: config.dotSize },
      uDotSpeed: { value: config.dotSpeed },
      uBrightness: { value: config.brightness }
    };
    const material = new THREE.ShaderMaterial({ vertexShader, fragmentShader, uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
    const mesh = new THREE.Mesh(new THREE.BufferGeometry(), material);
    const refMaterial = material.clone();
    refMaterial.uniforms.uIntensityMultiplier.value = 0.4;
    refMaterial.uniforms.uIsReflection.value = 1.0;
    const refMesh = new THREE.Mesh(new THREE.BufferGeometry(), refMaterial);
    refMesh.scale.y = -1; refMesh.position.y = -1.0;
    group.add(mesh, refMesh);
    trailMaterials.push(material.uniforms, refMaterial.uniforms);
    trailObjects.push({ mesh, refMesh, startX, thickness });
  }
}
function updateGeometries() {
  if (floorMesh.geometry) floorMesh.geometry.dispose();
  const floorGeo = new THREE.PlaneGeometry(1000, 1000, 1, 1500);
  floorGeo.rotateX(-Math.PI * 0.5);
  const pos = floorGeo.attributes.position.array;
  for (let i = 0; i < pos.length; i += 3) {
    if (pos[i + 2] < config.bendStartZ) {
      let d = config.bendStartZ - pos[i + 2];
      let maxA = config.arcRadius * Math.PI * 0.5;
      if (d < maxA) {
        let n = d / maxA;
        let a = (n * 0.4 + (n * n * (3.0 - 2.0 * n)) * 0.6) * (Math.PI * 0.5);
        pos[i + 1] = config.arcRadius * (1.0 - Math.cos(a));
        pos[i + 2] = (config.bendStartZ) - Math.sin(a) * config.arcRadius;
      } else {
        pos[i + 1] = config.arcRadius + (d - maxA);
        pos[i + 2] = config.bendStartZ - config.arcRadius;
      }
    }
  }
  floorGeo.computeVertexNormals();
  floorMesh.geometry = floorGeo;
  const bendUv = Math.abs(config.floorLength - config.bendStartZ) / (Math.abs(config.floorLength - config.bendStartZ) + (Math.PI * config.arcRadius) * 0.5 + Math.max(0.1, config.wallHeight - config.arcRadius));
  trailObjects.forEach(obj => {
    const path = new CycCurve(obj.startX, config.floorLength, config.bendStartZ - config.arcRadius, config.arcRadius, config.wallHeight);
    const geo = new THREE.TubeGeometry(path, 200, obj.thickness, 8, false);
    if (obj.mesh.geometry) obj.mesh.geometry.dispose();
    obj.mesh.geometry = obj.refMesh.geometry = geo;
    obj.mesh.material.uniforms.uBendUv.value = obj.refMesh.material.uniforms.uBendUv.value = bendUv;
  });
}
function onWindowResize() {
  if(!camera || !renderer || !composer) return;
  camera.aspect = getWidth() / getHeight();
  camera.updateProjectionMatrix();
  renderer.setSize(getWidth(), getHeight());
  composer.setSize(getWidth(), getHeight());
  if (smaaPass) smaaPass.setSize(getWidth() * config.dpr, getHeight() * config.dpr);
  if (blurPass && blurPass.uniforms && blurPass.uniforms.resolution) {
    blurPass.uniforms.resolution.value.set(getWidth() * config.dpr, getHeight() * config.dpr);
  }
}
function animate() {
  requestAnimationFrame(animate);
  if(!composer) return;
  globalTime += clock.getDelta() * config.speedMultiplier;
  trailMaterials.forEach(m => m.uTime.value = globalTime);
  composer.render();
}
