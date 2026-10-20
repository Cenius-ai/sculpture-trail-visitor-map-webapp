/* Local SVG trail projection: linear lat/lng projection, pan and zoom,
   focusable pins, and an accessible popup. No external tiles, no network. */
(function () {
  'use strict';

  var NS = 'http://www.w3.org/2000/svg';
  var VIEW_W = 1000;
  var VIEW_H = 640;
  var PAD = 64;
  var MIN_SCALE = 1;
  var MAX_SCALE = 6;

  function svgEl(name, attrs) {
    var node = document.createElementNS(NS, name);
    Object.keys(attrs || {}).forEach(function (key) {
      node.setAttribute(key, attrs[key]);
    });
    return node;
  }

  function readItems(list) {
    if (!list) return [];
    return Array.prototype.slice.call(list.querySelectorAll('li')).map(function (row) {
      return {
        id: row.getAttribute('data-sculpture-id'),
        title: row.getAttribute('data-title') || '',
        artist: row.getAttribute('data-artist') || '',
        material: row.getAttribute('data-material') || '',
        lat: parseFloat(row.getAttribute('data-lat')),
        lng: parseFloat(row.getAttribute('data-lng')),
        stageId: row.getAttribute('data-stage-id'),
        stageName: row.getAttribute('data-stage-name') || '',
        stageSequence: row.getAttribute('data-stage-sequence') || '',
        url: row.getAttribute('data-url') || '/',
        rating: row.getAttribute('data-rating') || ''
      };
    });
  }

  function createTrailMap(root) {
    if (!root) return null;
    var interactive = (root.getAttribute('data-mode') || 'interactive') === 'interactive';
    var svg = root.querySelector('svg');
    var viewport = root.querySelector('[data-map-viewport]');
    var pinLayer = root.querySelector('[data-map-pins]');
    var trailPath = root.querySelector('[data-map-trail]');
    var popup = root.querySelector('[data-map-popup]');
    var emptyState = root.querySelector('[data-map-empty]');
    var stageLayer = svgEl('g', { 'data-map-stages': '' });
    viewport.insertBefore(stageLayer, pinLayer);
    var controlScope = root.closest('.panel') || root;

    var bounds = {
      minLat: parseFloat(root.getAttribute('data-min-lat')) || 53.34,
      maxLat: parseFloat(root.getAttribute('data-max-lat')) || 53.356,
      minLng: parseFloat(root.getAttribute('data-min-lng')) || -1.842,
      maxLng: parseFloat(root.getAttribute('data-max-lng')) || -1.818
    };

    var state = { scale: 1, tx: 0, ty: 0 };
    var selectedId = null;
    var items = [];
    var pinNodes = {};

    function project(lat, lng) {
      var spanLng = bounds.maxLng - bounds.minLng || 1;
      var spanLat = bounds.maxLat - bounds.minLat || 1;
      var fx = (lng - bounds.minLng) / spanLng;
      var fy = (bounds.maxLat - lat) / spanLat;
      fx = Math.max(0, Math.min(1, fx));
      fy = Math.max(0, Math.min(1, fy));
      return { x: PAD + fx * (VIEW_W - PAD * 2), y: PAD + fy * (VIEW_H - PAD * 2) };
    }

    function applyTransform() {
      viewport.setAttribute(
        'transform',
        'translate(' + state.tx.toFixed(2) + ',' + state.ty.toFixed(2) + ') scale(' + state.scale.toFixed(3) + ')'
      );
      positionPopup();
    }

    function clampTransform() {
      var maxTx = 0;
      var minTx = -(state.scale - 1) * VIEW_W;
      var maxTy = 0;
      var minTy = -(state.scale - 1) * VIEW_H;
      state.tx = Math.min(maxTx, Math.max(minTx, state.tx));
      state.ty = Math.min(maxTy, Math.max(minTy, state.ty));
    }

    function positionPopup() {
      if (!popup || popup.hidden || !selectedId) return;
      var pin = pinNodes[selectedId];
      if (!pin) return;
      var point = { x: Number(pin.getAttribute('data-x')), y: Number(pin.getAttribute('data-y')) };
      var screenX = state.tx + point.x * state.scale;
      var screenY = state.ty + point.y * state.scale;
      var leftPct = Math.max(14, Math.min(86, (screenX / VIEW_W) * 100));
      var topPct = Math.max(8, Math.min(94, (screenY / VIEW_H) * 100));
      // Flip the card below the pin when there is no room above it.
      popup.classList.toggle('map-popup--below', screenY < VIEW_H * 0.44);
      popup.style.left = leftPct + '%';
      popup.style.top = topPct + '%';
    }

    function hidePopup() {
      if (!popup) return;
      popup.hidden = true;
      if (selectedId && pinNodes[selectedId]) {
        pinNodes[selectedId].classList.remove('pin--active');
        pinNodes[selectedId].setAttribute('aria-expanded', 'false');
      }
      selectedId = null;
    }

    function showPopup(item) {
      if (!popup) return;
      if (selectedId && pinNodes[selectedId] && selectedId !== item.id) {
        pinNodes[selectedId].classList.remove('pin--active');
        pinNodes[selectedId].setAttribute('aria-expanded', 'false');
      }
      selectedId = item.id;
      var pin = pinNodes[item.id];
      if (pin) {
        pin.classList.add('pin--active');
        pin.setAttribute('aria-expanded', 'true');
      }
      var titleNode = popup.querySelector('[data-popup-title]');
      var metaNode = popup.querySelector('[data-popup-meta]');
      var link = popup.querySelector('[data-popup-link]');
      if (titleNode) titleNode.textContent = item.title;
      if (metaNode) {
        metaNode.textContent =
          item.artist + ' · ' + item.material + ' · Stage ' + item.stageSequence + ' ' + item.stageName;
      }
      if (link) link.setAttribute('href', item.url);
      popup.hidden = false;
      positionPopup();
    }

    function activate(item) {
      if (interactive) showPopup(item);
      else if (item.url) window.location.assign(item.url);
    }

    function buildPins(list) {
      pinNodes = {};
      list.forEach(function (item) {
        var point = project(item.lat, item.lng);
        var pin = svgEl('g', {
          class: 'pin',
          tabindex: '0',
          role: 'button',
          'aria-label':
            item.title +
            ' by ' +
            item.artist +
            ', ' +
            item.material +
            ', stage ' +
            item.stageSequence +
            ' ' +
            item.stageName,
          'aria-expanded': 'false',
          'data-sculpture-id': item.id,
          'data-x': point.x,
          'data-y': point.y
        });
        pin.appendChild(svgEl('circle', { class: 'pin__halo', cx: point.x, cy: point.y, r: 14 }));
        pin.appendChild(svgEl('circle', { class: 'pin__dot', cx: point.x, cy: point.y, r: 7 }));
        var labelX = Math.max(110, Math.min(890, point.x));
        var label = svgEl('text', {
          class: 'pin__label',
          x: labelX,
          y: point.y + 32,
          'text-anchor': 'middle'
        });
        label.textContent = item.title;
        pin.appendChild(label);
        pin.addEventListener('click', function (event) {
          event.stopPropagation();
          activate(item);
        });
        pin.addEventListener('keydown', function (event) {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            activate(item);
          }
        });
        pinLayer.appendChild(pin);
        pinNodes[item.id] = pin;
      });
    }

    function buildStageMarkers(list) {
      var stagePositions = {};
      list.forEach(function (item) {
        var point = project(item.lat, item.lng);
        var entry = stagePositions[item.stageId];
        if (!entry) {
          stagePositions[item.stageId] = { x: point.x, y: point.y, count: 1, sequence: item.stageSequence };
        } else {
          entry.x += point.x;
          entry.y += point.y;
          entry.count += 1;
        }
      });
      Object.keys(stagePositions).forEach(function (stageId) {
        var entry = stagePositions[stageId];
        var cx = entry.x / entry.count;
        var cy = entry.y / entry.count;
        stageLayer.appendChild(svgEl('circle', { class: 'stage-marker__ring', cx: cx, cy: cy, r: 42 }));
        var label = svgEl('text', {
          class: 'stage-marker__text',
          x: cx,
          y: cy - 52,
          'text-anchor': 'middle'
        });
        label.textContent = 'Stage ' + entry.sequence;
        stageLayer.appendChild(label);
      });
    }

    function buildTrail(list) {
      if (!trailPath) return;
      if (list.length < 2) {
        trailPath.setAttribute('d', '');
        return;
      }
      var d = list
        .map(function (item, index) {
          var point = project(item.lat, item.lng);
          return (index === 0 ? 'M' : 'L') + point.x.toFixed(1) + ',' + point.y.toFixed(1);
        })
        .join(' ');
      trailPath.setAttribute('d', d);
    }

    function setData(list) {
      items = list || [];
      hidePopup();
      pinLayer.textContent = '';
      stageLayer.textContent = '';
      pinNodes = {};
      if (!items.length) {
        if (trailPath) trailPath.setAttribute('d', '');
        if (emptyState) emptyState.hidden = false;
        return;
      }
      if (emptyState) emptyState.hidden = true;
      buildStageMarkers(items);
      buildTrail(items);
      buildPins(items);
      applyTransform();
    }

    /* ---- pan and zoom (interactive maps only) ---- */
    if (interactive) {
      var dragging = false;
      var dragStart = null;

      svg.addEventListener('pointerdown', function (event) {
        if (event.button !== 0) return;
        if (event.target.closest && event.target.closest('.pin')) return;
        dragging = true;
        dragStart = { x: event.clientX, y: event.clientY, tx: state.tx, ty: state.ty };
        root.classList.add('is-panning');
        if (svg.setPointerCapture) svg.setPointerCapture(event.pointerId);
        hidePopup();
      });

      svg.addEventListener('pointermove', function (event) {
        if (!dragging || !dragStart) return;
        var rect = svg.getBoundingClientRect();
        var scaleX = VIEW_W / (rect.width || 1);
        var scaleY = VIEW_H / (rect.height || 1);
        state.tx = dragStart.tx + (event.clientX - dragStart.x) * scaleX;
        state.ty = dragStart.ty + (event.clientY - dragStart.y) * scaleY;
        clampTransform();
        applyTransform();
      });

      var endDrag = function () {
        dragging = false;
        dragStart = null;
        root.classList.remove('is-panning');
      };
      svg.addEventListener('pointerup', endDrag);
      svg.addEventListener('pointercancel', endDrag);
      window.addEventListener('pointerup', endDrag);

      var zoomAt = function (factor, clientX, clientY) {
        var rect = svg.getBoundingClientRect();
        var px = ((clientX - rect.left) / (rect.width || 1)) * VIEW_W;
        var py = ((clientY - rect.top) / (rect.height || 1)) * VIEW_H;
        var next = Math.min(MAX_SCALE, Math.max(MIN_SCALE, state.scale * factor));
        if (next === state.scale) return;
        state.tx = px - ((px - state.tx) * next) / state.scale;
        state.ty = py - ((py - state.ty) * next) / state.scale;
        state.scale = next;
        clampTransform();
        applyTransform();
      };

      svg.addEventListener(
        'wheel',
        function (event) {
          event.preventDefault();
          zoomAt(event.deltaY < 0 ? 1.16 : 1 / 1.16, event.clientX, event.clientY);
        },
        { passive: false }
      );

      controlScope.querySelectorAll('[data-map-zoom]').forEach(function (button) {
        button.addEventListener('click', function () {
          var rect = svg.getBoundingClientRect();
          var direction = button.getAttribute('data-map-zoom') === 'in' ? 1.35 : 1 / 1.35;
          zoomAt(direction, rect.left + rect.width / 2, rect.top + rect.height / 2);
        });
      });

      controlScope.querySelectorAll('[data-map-reset]').forEach(function (button) {
        button.addEventListener('click', function () {
          state.scale = 1;
          state.tx = 0;
          state.ty = 0;
          hidePopup();
          applyTransform();
        });
      });
    }

    if (popup) {
      var close = popup.querySelector('[data-popup-close]');
      if (close) close.addEventListener('click', hidePopup);
      document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') hidePopup();
      });
    }

    return {
      setData: setData,
      items: function () {
        return items;
      },
      select: function (sculptureId) {
        var item = items.filter(function (entry) {
          return String(entry.id) === String(sculptureId);
        })[0];
        if (item) showPopup(item);
      },
      reset: function () {
        state.scale = 1;
        state.tx = 0;
        state.ty = 0;
        hidePopup();
        applyTransform();
      }
    };
  }

  window.TrailMap = {
    create: createTrailMap,
    read: function (list) {
      return readItems(list);
    },
    svgEl: svgEl
  };
})();
