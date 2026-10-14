(() => {
  const player = window.LongChangScenePlayer.live({
    host: document.querySelector('#atlas-motion-view'),
    fullscreen: document.querySelector('#worlds .atlas-visual'),
    autoPlay: true,
    getScene() {
      const id = window.LongChangAtlas.currentScene(), item = window.SCENE_INDEX.find(scene => scene.id === id);
      return {id, poster:item.studio_poster, url:`data/interactive-scenes/${id}.json`};
    },
    async loadSimulation(config, status) {
      const {createSceneSimulation} = await import('./scene-physics.js');
      return createSceneSimulation(config, status);
    },
    onWorld: world => { window.SceneRoom = world; },
  });
  const view = () => player.setActive(document.querySelector('#scene-detail').dataset.view === 'motion');
  document.addEventListener('longchang:scene', () => player.select());
  document.addEventListener('longchang:atlas-view', view);
  window.LongChangSceneLive = Object.freeze({open:player.open, current:player.current});
  view();
})();
