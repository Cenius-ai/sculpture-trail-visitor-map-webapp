/* Curator studio: create, edit, and delete sculptures and stages against the
   real API, with inline validation, delete confirmation, and live list refresh. */
(function () {
  'use strict';

  var Trail = window.Trail;
  if (!Trail) return;

  var banner = document.getElementById('curator-banner');
  var errorBanner = document.getElementById('curator-error');
  var sculptureForm = document.getElementById('sculpture-form');
  var stageForm = document.getElementById('stage-form');
  var sculptureRows = document.querySelector('[data-sculpture-rows]');
  var stageRows = document.querySelector('[data-stage-rows]');
  var stageSelect = document.getElementById('sculpture-stage');
  var confirmDialog = document.getElementById('confirm-dialog');
  var confirmState = null;

  function say(message, kind) {
    if (kind === 'error') {
      Trail.showBanner(errorBanner, message, 'error');
      Trail.showBanner(banner, '');
    } else {
      Trail.showBanner(banner, message, 'success');
      Trail.showBanner(errorBanner, '');
    }
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function coord(value, positive, negative) {
    var number = Number(value);
    if (!isFinite(number)) return '—';
    return Math.abs(number).toFixed(4) + '° ' + (number >= 0 ? positive : negative);
  }

  function countUpdate() {
    var sculptureCount = sculptureRows ? sculptureRows.children.length : 0;
    var stageCount = stageRows ? stageRows.children.length : 0;
    var sculptureLabel = document.querySelector('[data-sculpture-count]');
    var stageLabel = document.querySelector('[data-stage-count]');
    if (sculptureLabel) sculptureLabel.textContent = sculptureCount + ' on the trail';
    if (stageLabel) stageLabel.textContent = stageCount + ' on the trail';

    var sculptureEmpty = document.querySelector('[data-sculpture-empty]');
    var stageEmpty = document.querySelector('[data-stage-empty]');
    if (sculptureEmpty) sculptureEmpty.hidden = sculptureCount !== 0;
    if (stageEmpty) stageEmpty.hidden = stageCount !== 0;
    document.querySelectorAll('[data-empty-table]').forEach(function (wrap) {
      var body = wrap.querySelector('tbody');
      wrap.hidden = !body || body.children.length === 0;
    });
  }

  /* ---- confirm dialog ------------------------------------------------- */
  function askConfirm(message) {
    if (!confirmDialog || typeof confirmDialog.showModal !== 'function') {
      return Promise.resolve(window.confirm(message));
    }
    if (confirmState) return confirmState.promise;
    var messageNode = confirmDialog.querySelector('#confirm-message');
    if (messageNode) messageNode.textContent = message;
    var resolve;
    var promise = new Promise(function (done) {
      resolve = done;
    });
    confirmState = { promise: promise, resolve: resolve };
    confirmDialog.showModal();
    return promise;
  }

  function settleConfirm(answer) {
    if (!confirmState) return;
    var state = confirmState;
    confirmState = null;
    if (confirmDialog && confirmDialog.open) confirmDialog.close();
    state.resolve(answer);
  }

  if (confirmDialog) {
    confirmDialog.querySelector('[data-confirm-ok]').addEventListener('click', function () {
      settleConfirm(true);
    });
    confirmDialog.querySelector('[data-confirm-cancel]').addEventListener('click', function () {
      settleConfirm(false);
    });
    confirmDialog.addEventListener('cancel', function (event) {
      event.preventDefault();
      settleConfirm(false);
    });
  }

  /* ---- sculpture rows ------------------------------------------------- */
  function sculptureRow(sculpture) {
    var tr = document.createElement('tr');
    tr.setAttribute('data-sculpture-row', sculpture.id);

    var titleCell = el('td', 'cell-title');
    var link = el('a', null, sculpture.title);
    link.setAttribute('href', '/sculptures/' + sculpture.id);
    titleCell.appendChild(link);
    titleCell.appendChild(el('div', 'field__hint', sculpture.artist + ' · ' + sculpture.material));

    var stageCell = el('td', null, sculpture.stage.sequence + '. ' + sculpture.stage.name);
    var coordCell = el(
      'td',
      'num',
      coord(sculpture.lat, 'N', 'S') + ' / ' + coord(sculpture.lng, 'E', 'W')
    );

    var actionCell = el('td');
    var actions = el('div', 'row-actions');
    var edit = el('button', 'btn btn--sm', 'Edit');
    edit.type = 'button';
    edit.setAttribute('data-edit-sculpture', sculpture.id);
    edit.setAttribute('aria-label', 'Edit ' + sculpture.title);
    var remove = el('button', 'btn btn--sm btn--danger', 'Delete');
    remove.type = 'button';
    remove.setAttribute('data-delete-sculpture', sculpture.id);
    remove.setAttribute('aria-label', 'Delete ' + sculpture.title);
    actions.appendChild(edit);
    actions.appendChild(remove);
    actionCell.appendChild(actions);

    tr.appendChild(titleCell);
    tr.appendChild(stageCell);
    tr.appendChild(coordCell);
    tr.appendChild(actionCell);
    return tr;
  }

  function stageRow(stage) {
    var tr = document.createElement('tr');
    tr.setAttribute('data-stage-row', stage.id);
    tr.appendChild(el('td', 'num', String(stage.sequence)));

    var nameCell = el('td', 'cell-title');
    var link = el('a', null, stage.name);
    link.setAttribute('href', '/stages/' + stage.id);
    nameCell.appendChild(link);
    var notes = stage.accessibility_notes || '';
    nameCell.appendChild(el('div', 'field__hint', notes.length > 68 ? notes.slice(0, 68) + '…' : notes));

    var piecesCell = el('td', 'num', String(stage.sculpture_count || 0));
    piecesCell.setAttribute('data-stage-pieces', stage.id);

    var actionCell = el('td');
    var actions = el('div', 'row-actions');
    var edit = el('button', 'btn btn--sm', 'Edit');
    edit.type = 'button';
    edit.setAttribute('data-edit-stage', stage.id);
    edit.setAttribute('aria-label', 'Edit ' + stage.name);
    var remove = el('button', 'btn btn--sm btn--danger', 'Delete');
    remove.type = 'button';
    remove.setAttribute('data-delete-stage', stage.id);
    remove.setAttribute('aria-label', 'Delete ' + stage.name);
    actions.appendChild(edit);
    actions.appendChild(remove);
    actionCell.appendChild(actions);

    tr.appendChild(nameCell);
    tr.appendChild(piecesCell);
    tr.appendChild(actionCell);
    return tr;
  }

  function replaceOrAppend(container, attribute, newRow, id) {
    var existing = container.querySelector('[' + attribute + '="' + id + '"]');
    if (existing) container.replaceChild(newRow, existing);
    else container.appendChild(newRow);
    countUpdate();
  }

  function optionFor(stage) {
    return stageSelect ? stageSelect.querySelector('option[value="' + stage.id + '"]') : null;
  }

  /* ---- sculpture form ------------------------------------------------- */
  function sculpturePayload() {
    return {
      title: sculptureForm.querySelector('[name="title"]').value.trim(),
      artist: sculptureForm.querySelector('[name="artist"]').value.trim(),
      material: sculptureForm.querySelector('[name="material"]').value.trim(),
      stage_id: sculptureForm.querySelector('[name="stage_id"]').value,
      lat: sculptureForm.querySelector('[name="lat"]').value,
      lng: sculptureForm.querySelector('[name="lng"]').value,
      description: sculptureForm.querySelector('[name="description"]').value.trim()
    };
  }

  function validateSculpture(payload) {
    var errors = {};
    if (payload.title.length < 2) errors.title = 'Enter a title of at least 2 characters.';
    if (payload.artist.length < 2) errors.artist = 'Enter the artist name.';
    if (payload.material.length < 2) errors.material = 'Enter the material.';
    if (!payload.stage_id) errors.stage_id = 'Choose a trail stage.';
    var lat = Number(payload.lat);
    if (payload.lat === '' || !isFinite(lat)) errors.lat = 'Enter a latitude in decimal degrees.';
    else if (lat < -90 || lat > 90) errors.lat = 'Latitude must be between -90 and 90.';
    var lng = Number(payload.lng);
    if (payload.lng === '' || !isFinite(lng)) errors.lng = 'Enter a longitude in decimal degrees.';
    else if (lng < -180 || lng > 180) errors.lng = 'Longitude must be between -180 and 180.';
    if (payload.description.length < 20) errors.description = 'Describe the piece in at least 20 characters.';
    return errors;
  }

  function resetSculptureForm() {
    sculptureForm.reset();
    sculptureForm.setAttribute('data-mode', 'create');
    sculptureForm.setAttribute('data-id', '');
    Trail.clearErrors(sculptureForm);
    var lat = sculptureForm.querySelector('[name="lat"]');
    var lng = sculptureForm.querySelector('[name="lng"]');
    if (lat) lat.value = '53.3480';
    if (lng) lng.value = '-1.8300';
    var heading = document.querySelector('[data-sculpture-form-title]');
    if (heading) heading.textContent = 'Add a sculpture';
    var cancel = document.querySelector('[data-cancel-sculpture]');
    if (cancel) cancel.hidden = true;
    var submit = sculptureForm.querySelector('button[type="submit"]');
    if (submit) {
      submit.querySelector('.btn__label').textContent = 'Save sculpture';
    }
  }

  if (sculptureForm) {
    sculptureForm.addEventListener('submit', function (event) {
      event.preventDefault();
      var payload = sculpturePayload();
      var errors = validateSculpture(payload);
      if (Object.keys(errors).length) {
        Trail.setErrors(sculptureForm, errors, 'Check the highlighted sculpture fields.');
        return;
      }
      var mode = sculptureForm.getAttribute('data-mode');
      var id = sculptureForm.getAttribute('data-id');
      var submit = sculptureForm.querySelector('button[type="submit"]');
      if (submit.getAttribute('data-busy') === 'true') return;
      Trail.setBusy(submit, true);
      Trail.setErrors(sculptureForm, {});

      var request =
        mode === 'edit'
          ? Trail.api('/api/sculptures/' + encodeURIComponent(id), { method: 'PATCH', body: payload })
          : Trail.api('/api/sculptures', { method: 'POST', body: payload });

      request
        .then(function (data) {
          replaceOrAppend(
            sculptureRows,
            'data-sculpture-row',
            sculptureRow(data.sculpture),
            data.sculpture.id
          );
          Trail.flash(sculptureRows.querySelector('[data-sculpture-row="' + data.sculpture.id + '"]'), 'ok');
          say(
            mode === 'edit'
              ? 'Saved “' + data.sculpture.title + '”.'
              : 'Added “' + data.sculpture.title + '” to the trail.'
          );
          resetSculptureForm();
        })
        .catch(function (error) {
          Trail.setErrors(sculptureForm, error.fields || {}, error.message);
          say(error.message, 'error');
        })
        .then(function () {
          Trail.setBusy(submit, false);
        });
    });

    var cancelSculpture = document.querySelector('[data-cancel-sculpture]');
    if (cancelSculpture) {
      cancelSculpture.addEventListener('click', function () {
        resetSculptureForm();
        say('Edit cancelled.');
      });
    }
  }

  /* ---- stage form ----------------------------------------------------- */
  function stagePayload() {
    return {
      name: stageForm.querySelector('[name="name"]').value.trim(),
      sequence: stageForm.querySelector('[name="sequence"]').value,
      description: stageForm.querySelector('[name="description"]').value.trim(),
      accessibility_notes: stageForm.querySelector('[name="accessibility_notes"]').value.trim()
    };
  }

  function validateStage(payload) {
    var errors = {};
    if (payload.name.length < 3) errors.name = 'Enter a stage name of at least 3 characters.';
    var sequence = Number(payload.sequence);
    if (payload.sequence === '' || !isFinite(sequence) || sequence < 1 || sequence > 99) {
      errors.sequence = 'Stage number must be between 1 and 99.';
    }
    if (payload.description.length < 10) errors.description = 'Add a description of at least 10 characters.';
    if (payload.accessibility_notes.length < 10) {
      errors.accessibility_notes = 'Add accessibility notes of at least 10 characters.';
    }
    return errors;
  }

  function resetStageForm() {
    stageForm.reset();
    stageForm.setAttribute('data-mode', 'create');
    stageForm.setAttribute('data-id', '');
    Trail.clearErrors(stageForm);
    var sequence = stageForm.querySelector('[name="sequence"]');
    if (sequence) sequence.value = String(stageRows ? stageRows.children.length + 1 : 1);
    var heading = document.querySelector('[data-stage-form-title]');
    if (heading) heading.textContent = 'Add a trail stage';
    var cancel = document.querySelector('[data-cancel-stage]');
    if (cancel) cancel.hidden = true;
    var submit = stageForm.querySelector('button[type="submit"]');
    if (submit) submit.querySelector('.btn__label').textContent = 'Save stage';
  }

  if (stageForm) {
    stageForm.addEventListener('submit', function (event) {
      event.preventDefault();
      var payload = stagePayload();
      var errors = validateStage(payload);
      if (Object.keys(errors).length) {
        Trail.setErrors(stageForm, errors, 'Check the highlighted stage fields.');
        return;
      }
      var mode = stageForm.getAttribute('data-mode');
      var id = stageForm.getAttribute('data-id');
      var submit = stageForm.querySelector('button[type="submit"]');
      if (submit.getAttribute('data-busy') === 'true') return;
      Trail.setBusy(submit, true);
      Trail.setErrors(stageForm, {});

      var request =
        mode === 'edit'
          ? Trail.api('/api/stages/' + encodeURIComponent(id), { method: 'PATCH', body: payload })
          : Trail.api('/api/stages', { method: 'POST', body: payload });

      request
        .then(function (data) {
          replaceOrAppend(stageRows, 'data-stage-row', stageRow(data.stage), data.stage.id);
          Trail.flash(stageRows.querySelector('[data-stage-row="' + data.stage.id + '"]'), 'ok');
          if (stageSelect) {
            var option = optionFor(data.stage);
            if (option) {
              option.textContent = data.stage.sequence + '. ' + data.stage.name;
            } else {
              var fresh = document.createElement('option');
              fresh.value = data.stage.id;
              fresh.textContent = data.stage.sequence + '. ' + data.stage.name;
              stageSelect.appendChild(fresh);
            }
          }
          say(
            mode === 'edit'
              ? 'Saved “' + data.stage.name + '”.'
              : 'Added the “' + data.stage.name + '” stage.'
          );
          resetStageForm();
        })
        .catch(function (error) {
          Trail.setErrors(stageForm, error.fields || {}, error.message);
          say(error.message, 'error');
        })
        .then(function () {
          Trail.setBusy(submit, false);
        });
    });

    var cancelStage = document.querySelector('[data-cancel-stage]');
    if (cancelStage) {
      cancelStage.addEventListener('click', function () {
        resetStageForm();
        say('Edit cancelled.');
      });
    }
  }

  /* ---- edit / delete delegation --------------------------------------- */
  function loadSculpture(id) {
    Trail.api('/api/sculptures/' + encodeURIComponent(id))
      .then(function (data) {
        var sculpture = data.sculpture;
        sculptureForm.setAttribute('data-mode', 'edit');
        sculptureForm.setAttribute('data-id', sculpture.id);
        sculptureForm.querySelector('[name="title"]').value = sculpture.title;
        sculptureForm.querySelector('[name="artist"]').value = sculpture.artist;
        sculptureForm.querySelector('[name="material"]').value = sculpture.material;
        sculptureForm.querySelector('[name="description"]').value = sculpture.description;
        sculptureForm.querySelector('[name="lat"]').value = sculpture.lat;
        sculptureForm.querySelector('[name="lng"]').value = sculpture.lng;
        if (stageSelect) stageSelect.value = String(sculpture.stage.id);
        var heading = document.querySelector('[data-sculpture-form-title]');
        if (heading) heading.textContent = 'Edit “' + sculpture.title + '”';
        var cancel = document.querySelector('[data-cancel-sculpture]');
        if (cancel) cancel.hidden = false;
        var submit = sculptureForm.querySelector('button[type="submit"]');
        if (submit) submit.querySelector('.btn__label').textContent = 'Save changes';
        Trail.clearErrors(sculptureForm);
        sculptureForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
        sculptureForm.querySelector('[name="title"]').focus();
      })
      .catch(function (error) {
        say(error.message, 'error');
      });
  }

  function loadStage(id) {
    Trail.api('/api/stages/' + encodeURIComponent(id))
      .then(function (data) {
        var stage = data.stage;
        stageForm.setAttribute('data-mode', 'edit');
        stageForm.setAttribute('data-id', stage.id);
        stageForm.querySelector('[name="name"]').value = stage.name;
        stageForm.querySelector('[name="sequence"]').value = stage.sequence;
        stageForm.querySelector('[name="description"]').value = stage.description;
        stageForm.querySelector('[name="accessibility_notes"]').value = stage.accessibility_notes;
        var heading = document.querySelector('[data-stage-form-title]');
        if (heading) heading.textContent = 'Edit “' + stage.name + '”';
        var cancel = document.querySelector('[data-cancel-stage]');
        if (cancel) cancel.hidden = false;
        var submit = stageForm.querySelector('button[type="submit"]');
        if (submit) submit.querySelector('.btn__label').textContent = 'Save changes';
        Trail.clearErrors(stageForm);
        stageForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
        stageForm.querySelector('[name="name"]').focus();
      })
      .catch(function (error) {
        say(error.message, 'error');
      });
  }

  function deleteSculpture(id, title) {
    askConfirm('Delete “' + title + '” and every visitor note left on it?').then(function (confirmed) {
      if (!confirmed) return;
      Trail.api('/api/sculptures/' + encodeURIComponent(id), { method: 'DELETE' })
        .then(function () {
          var row = sculptureRows.querySelector('[data-sculpture-row="' + id + '"]');
          if (row) row.remove();
          if (sculptureForm.getAttribute('data-id') === String(id)) resetSculptureForm();
          countUpdate();
          say('Deleted “' + title + '”.');
        })
        .catch(function (error) {
          say(error.message, 'error');
        });
    });
  }

  function deleteStage(id, name) {
    askConfirm('Delete the “' + name + '” stage? Stages can only be deleted when no sculptures are assigned.').then(
      function (confirmed) {
        if (!confirmed) return;
        Trail.api('/api/stages/' + encodeURIComponent(id), { method: 'DELETE' })
          .then(function () {
            var row = stageRows.querySelector('[data-stage-row="' + id + '"]');
            if (row) row.remove();
            var option = stageSelect ? stageSelect.querySelector('option[value="' + id + '"]') : null;
            if (option) option.remove();
            if (stageForm.getAttribute('data-id') === String(id)) resetStageForm();
            countUpdate();
            say('Deleted the “' + name + '” stage.');
          })
          .catch(function (error) {
            say(error.message, 'error');
          });
      }
    );
  }

  if (sculptureRows) {
    sculptureRows.addEventListener('click', function (event) {
      var editButton = event.target.closest('[data-edit-sculpture]');
      if (editButton) {
        loadSculpture(editButton.getAttribute('data-edit-sculpture'));
        return;
      }
      var deleteButton = event.target.closest('[data-delete-sculpture]');
      if (deleteButton) {
        var row = deleteButton.closest('tr');
        var title = row ? row.querySelector('.cell-title a').textContent : 'this sculpture';
        deleteSculpture(deleteButton.getAttribute('data-delete-sculpture'), title);
      }
    });
  }

  if (stageRows) {
    stageRows.addEventListener('click', function (event) {
      var editButton = event.target.closest('[data-edit-stage]');
      if (editButton) {
        loadStage(editButton.getAttribute('data-edit-stage'));
        return;
      }
      var deleteButton = event.target.closest('[data-delete-stage]');
      if (deleteButton) {
        var row = deleteButton.closest('tr');
        var name = row ? row.querySelector('.cell-title a').textContent : 'this stage';
        deleteStage(deleteButton.getAttribute('data-delete-stage'), name);
      }
    });
  }

  countUpdate();
})();
