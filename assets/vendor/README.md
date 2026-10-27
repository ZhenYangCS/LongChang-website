# Local browser dependencies

- `mujoco/`: official `@mujoco/mujoco` 3.15.0, from the npm registry. Apache-2.0. Source: https://github.com/google-deepmind/mujoco/tree/main/wasm
- `three/`: Three.js 0.186.1, from the npm registry. MIT. Source: https://github.com/mrdoob/three.js

Three.js addon imports point to the local ES module instead of a bare package specifier. No runtime CDN requests are made. Physics downloads on interaction/hover, or when a touch screen approaches an interactive region after the page has loaded (except in Data Saver mode). The single-threaded WASM build requires no cross-origin isolation headers.
