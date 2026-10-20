/* Stage detail: the static location plan for the stage's sculptures. */
(function () {
  'use strict';

  var root = document.getElementById('map');
  var dataList = document.getElementById('trail-data');
  if (!root || !dataList || !window.TrailMap) return;

  var map = window.TrailMap.create(root);
  map.setData(window.TrailMap.read(dataList));
})();
