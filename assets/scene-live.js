(() => {
  const player = window.LongChangScenePlayer.live({
    host: document.querySelector('#atlas-motion-view'),
    fullscreen: document.querySelector('#worlds .atlas-visual'),
    autoPlay: false,
    getScene() {
      const id = window.LongChangAtlas.currentScene();
      return {id, poster:`assets/images/interactive-room-${id}.webp`, url:`data/interactive-scenes/${id}.json`};
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
  const tab = document.querySelector('[data-atlas-view="motion"]');
  tab.addEventListener('pointerenter', player.prepare, {passive:true});
  tab.addEventListener('focus', player.prepare);
  window.LongChangSceneLive = Object.freeze({open:player.open, current:player.current});
  view();
})();
