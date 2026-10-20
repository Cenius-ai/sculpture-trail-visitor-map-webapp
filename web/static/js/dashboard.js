/* Trail map dashboard: stage filter with a real API request, loading and
   error states, and linked stage cards / index rows. */
(function () {
  'use strict';

  var Trail = window.Trail;
  var root = document.getElementById('map');
  var dataList = document.getElementById('trail-data');
  if (!root || !dataList || !window.TrailMap) return;

  var map = window.TrailMap.create(root);
  var initial = window.TrailMap.read(dataList);
  map.setData(initial);

  var filter = document.getElementById('stage-filter');
  var errorBanner = document.getElementById('dashboard-error');
  var retryButton = errorBanner ? errorBanner.querySelector('[data-retry]') : null;
  var stageItems = Array.prototype.slice.call(document.querySelectorAll('[data-stage-item]'));
  var indexRows = Array.prototype.slice.call(document.querySelectorAll('[data-index-row]'));
  var indexCount = document.querySelector('[data-index-count]');
  var mapSummary = document.querySelector('[data-map-summary]');
  var clearButtons = Array.prototype.slice.call(document.querySelectorAll('[data-clear-filter]'));
  var emptyTitle = root.querySelector('[data-map-empty-title]');
  var emptyText = root.querySelector('[data-map-empty-text]');
  var indexEmpty = document.querySelector('[data-index-empty]');
  var indexBody = document.querySelector('[data-index-body]');
  var indexWrap = indexBody ? indexBody.closest('.table-wrap') : null;
  var currentStage = 'all';
  var inFlight = false;

  function fromApi(sculpture) {
    return {
      id: String(sculpture.id),
      title: sculpture.title,
      artist: sculpture.artist,
      material: sculpture.material,
      lat: sculpture.lat,
      lng: sculpture.lng,
      stageId: String(sculpture.stage.id),
      stageName: sculpture.stage.name,
      stageSequence: String(sculpture.stage.sequence),
      url: '/sculptures/' + sculpture.id,
      rating: sculpture.average_rating === null || sculpture.average_rating === undefined ? '' : String(sculpture.average_rating)
    };
  }

  function apply(stageId, items) {
    var filtered = stageId !== 'all';
    if (emptyTitle && emptyText) {
      emptyTitle.textContent = filtered ? 'No sculptures on this stage yet' : 'No sculptures on the trail yet';
      emptyText.textContent = filtered
        ? 'Clear the stage filter to see the whole trail.'
        : 'Trail curators can add the first piece in the curator studio.';
    }
    map.setData(items);

    stageItems.forEach(function (item) {
      item.hidden = filtered && item.getAttribute('data-stage-item') !== String(stageId);
    });
    indexRows.forEach(function (row) {
      row.hidden = filtered && row.getAttribute('data-stage-id') !== String(stageId);
    });
    if (indexCount) indexCount.textContent = items.length + ' shown';
    if (mapSummary) mapSummary.textContent = items.length + (items.length === 1 ? ' pin' : ' pins');
    if (indexWrap) indexWrap.hidden = items.length === 0;
    if (indexEmpty) indexEmpty.hidden = items.length !== 0;
    clearButtons.forEach(function (button) {
      button.hidden = !filtered;
    });
  }

  function load(stageId) {
    if (inFlight) return;
    inFlight = true;
    currentStage = stageId;
    root.setAttribute('data-loading', 'true');
    var url = stageId === 'all' ? '/api/sculptures' : '/api/sculptures?stage_id=' + encodeURIComponent(stageId);
    Trail.api(url)
      .then(function (data) {
        apply(stageId, data.sculptures.map(fromApi));
        Trail.showBanner(errorBanner, '');
      })
      .catch(function (error) {
        Trail.showBanner(errorBanner, error.message || 'We could not refresh the trail data.');
      })
      .then(function () {
        root.removeAttribute('data-loading');
        inFlight = false;
      });
  }

  if (filter) {
    filter.addEventListener('change', function () {
      load(filter.value);
    });
  }

  clearButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      if (filter) filter.value = 'all';
      load('all');
    });
  });

  if (retryButton) {
    retryButton.addEventListener('click', function () {
      load(currentStage);
    });
  }

  var focusId = new URLSearchParams(window.location.search).get('focus');
  if (focusId) map.select(focusId);
})();
