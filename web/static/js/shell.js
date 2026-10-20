/* Shared shell behaviour: command palette and small DOM/API helpers.
   Everything hangs off window.Trail so the plain scripts cannot collide. */
(function () {
  'use strict';

  var Trail = window.Trail || {};
  window.Trail = Trail;

  Trail.api = function (url, options) {
    var opts = Object.assign(
      { headers: { Accept: 'application/json' }, credentials: 'same-origin' },
      options || {}
    );
    if (opts.body && typeof opts.body !== 'string') {
      opts.headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
      opts.body = JSON.stringify(opts.body);
    }
    return fetch(url, opts).then(function (response) {
      return response
        .json()
        .catch(function () {
          return {};
        })
        .then(function (data) {
          if (!response.ok) {
            var detail = (data && data.error) || {};
            var error = new Error(detail.message || 'That request could not be completed.');
            error.status = response.status;
            error.code = detail.code;
            error.fields = detail.fields || {};
            throw error;
          }
          return data;
        });
    });
  };

  Trail.clearErrors = function (form) {
    if (!form) return;
    form.querySelectorAll('[data-error-for]').forEach(function (node) {
      node.textContent = '';
    });
    form.querySelectorAll('[aria-invalid="true"]').forEach(function (node) {
      node.removeAttribute('aria-invalid');
    });
    var banner = form.querySelector('[data-form-error]');
    if (banner) banner.textContent = '';
  };

  Trail.setErrors = function (form, fields, message) {
    Trail.clearErrors(form);
    if (!form) return;
    var first = null;
    Object.keys(fields || {}).forEach(function (name) {
      var slot = form.querySelector('[data-error-for="' + name + '"]');
      var input = form.querySelector('[name="' + name + '"]');
      if (slot) slot.textContent = fields[name];
      if (input) {
        input.setAttribute('aria-invalid', 'true');
        if (!first) first = input;
      }
    });
    var banner = form.querySelector('[data-form-error]');
    if (banner && message) banner.textContent = message;
    if (first && typeof first.focus === 'function') first.focus();
  };

  Trail.setBusy = function (button, busy) {
    if (!button) return;
    if (busy) {
      button.setAttribute('data-busy', 'true');
      button.setAttribute('disabled', 'disabled');
      button.setAttribute('aria-busy', 'true');
    } else {
      button.removeAttribute('data-busy');
      button.removeAttribute('disabled');
      button.removeAttribute('aria-busy');
    }
  };

  Trail.flash = function (element, kind) {
    if (!element) return;
    var cls = kind === 'error' ? 'flash-err' : 'flash-ok';
    element.classList.remove('flash-ok', 'flash-err');
    // Force a reflow so the animation restarts on repeated updates.
    void element.offsetWidth;
    element.classList.add(cls);
    element.addEventListener('animationend', function handler() {
      element.classList.remove(cls);
      element.removeEventListener('animationend', handler);
    });
  };

  Trail.showBanner = function (element, message, kind) {
    if (!element) return;
    element.hidden = !message;
    element.classList.toggle('banner--ok', kind === 'success');
    var text = element.querySelector('[data-error-text]') || element.querySelector('[data-banner-text]');
    if (text) text.textContent = message || '';
  };

  Trail.formatDate = function (value) {
    if (!value) return '';
    var parts = String(value).split(' ');
    var dateBits = (parts[0] || '').split('-');
    if (dateBits.length !== 3) return String(value);
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return parseInt(dateBits[2], 10) + ' ' + months[parseInt(dateBits[1], 10) - 1] + ' ' + dateBits[0];
  };

  Trail.stars = function (rating) {
    var filled = Math.max(0, Math.min(5, Math.round(Number(rating) || 0)));
    return '★★★★★'.slice(0, filled) + '☆☆☆☆☆'.slice(0, 5 - filled);
  };

  /* ---- command palette ------------------------------------------------ */
  var dialog = document.getElementById('palette');
  if (dialog && typeof dialog.showModal === 'function') {
    var input = document.getElementById('palette-input');
    var list = document.getElementById('palette-list');
    var empty = document.getElementById('palette-empty');
    var links = Array.prototype.slice.call(list.querySelectorAll('a'));
    var activeIndex = -1;

    var matching = function () {
      return links.filter(function (link) {
        return !link.parentElement.hidden;
      });
    };

    var setActive = function (index) {
      var visible = matching();
      links.forEach(function (link) {
        link.classList.remove('is-active');
      });
      if (!visible.length) {
        activeIndex = -1;
        return;
      }
      activeIndex = (index + visible.length) % visible.length;
      var link = visible[activeIndex];
      link.classList.add('is-active');
      link.setAttribute('aria-selected', 'true');
      if (link.scrollIntoView) link.scrollIntoView({ block: 'nearest' });
    };

    var filter = function (term) {
      var query = (term || '').trim().toLowerCase();
      links.forEach(function (link) {
        var haystack = (link.getAttribute('data-search') || link.textContent).toLowerCase();
        var matches = !query || haystack.indexOf(query) !== -1;
        link.parentElement.hidden = !matches;
        link.removeAttribute('aria-selected');
        link.classList.remove('is-active');
      });
      var visible = matching();
      empty.hidden = visible.length > 0;
      activeIndex = -1;
      if (visible.length) setActive(0);
    };

    var openPalette = function () {
      input.value = '';
      filter('');
      dialog.showModal();
      input.focus();
    };

    document.querySelectorAll('[data-palette-open]').forEach(function (trigger) {
      trigger.addEventListener('click', openPalette);
    });

    input.addEventListener('input', function () {
      filter(input.value);
    });

    input.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActive(activeIndex + 1);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActive(activeIndex - 1);
      } else if (event.key === 'Enter') {
        var visible = matching();
        if (visible.length) {
          event.preventDefault();
          var target = activeIndex >= 0 ? visible[activeIndex] : visible[0];
          window.location.assign(target.getAttribute('href'));
        }
      }
    });

    document.addEventListener('keydown', function (event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        if (dialog.open) dialog.close();
        else openPalette();
      }
    });

    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) dialog.close();
    });
  }
})();
