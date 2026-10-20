/* Sculpture detail: post feedback, update the average in place, keep the
   value on failure, and never submit twice. */
(function () {
  'use strict';

  var Trail = window.Trail;
  var form = document.getElementById('feedback-form');
  if (!form) return;

  var grid = document.querySelector('.detail-grid[data-sculpture-id]');
  if (!grid) return;
  var sculptureId = grid.getAttribute('data-sculpture-id');

  var list = document.querySelector('[data-feedback-list]');
  var emptyItem = document.querySelector('[data-feedback-empty]');
  var averageNode = document.querySelector('[data-average]');
  var starsNode = document.querySelector('[data-stars]');
  var countNode = document.querySelector('[data-count]');
  var submit = form.querySelector('button[type="submit"]');
  var status = form.querySelector('[data-feedback-status]');
  var comment = form.querySelector('[name="comment"]');
  var submitting = false;

  function chosenRating() {
    var checked = form.querySelector('input[name="rating"]:checked');
    return checked ? Number(checked.value) : 0;
  }

  function validate() {
    var errors = {};
    if (!chosenRating()) errors.rating = 'Choose a star rating.';
    var text = comment.value.trim();
    if (text.length < 3) errors.comment = 'Add a few words — at least 3 characters.';
    if (text.length > 1000) errors.comment = 'Keep your comment to 1000 characters or fewer.';
    return errors;
  }

  function feedbackItem(item) {
    var row = document.createElement('li');
    row.className = 'feedback-item';

    var head = document.createElement('div');
    head.className = 'feedback-item__head';

    var author = document.createElement('span');
    author.className = 'feedback-item__author';
    author.textContent = item.author;

    var stars = document.createElement('span');
    stars.className = 'stars-display';
    stars.setAttribute('aria-label', item.rating + ' out of 5');
    stars.textContent = Trail.stars(item.rating);

    var date = document.createElement('span');
    date.className = 'feedback-item__date';
    date.textContent = Trail.formatDate(item.created_at);

    head.appendChild(author);
    head.appendChild(stars);
    head.appendChild(date);

    var body = document.createElement('p');
    body.className = 'feedback-item__comment';
    body.textContent = item.comment;

    row.appendChild(head);
    row.appendChild(body);
    return row;
  }

  function updateStats(stats) {
    if (averageNode) {
      averageNode.textContent = stats.average === null || stats.average === undefined ? '—' : Number(stats.average).toFixed(1);
    }
    if (starsNode) starsNode.textContent = Trail.stars(stats.average);
    if (countNode) countNode.textContent = stats.count + (stats.count === 1 ? ' note' : ' notes');
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (submitting) return;
    var errors = validate();
    if (Object.keys(errors).length) {
      Trail.setErrors(form, errors);
      return;
    }
    submitting = true;
    Trail.setErrors(form, {});
    Trail.setBusy(submit, true);

    Trail.api('/api/sculptures/' + encodeURIComponent(sculptureId) + '/feedback', {
      method: 'POST',
      body: { rating: chosenRating(), comment: comment.value.trim() }
    })
      .then(function (data) {
        if (list) {
          list.insertBefore(feedbackItem(data.feedback), list.firstChild);
          Trail.flash(list.firstElementChild, 'ok');
        }
        if (emptyItem) emptyItem.hidden = true;
        updateStats(data.stats);
        form.reset();
        if (status) status.textContent = 'Feedback posted. Thank you.';
        if (comment) comment.value = '';
      })
      .catch(function (error) {
        Trail.setErrors(form, error.fields || {}, error.message);
      })
      .then(function () {
        submitting = false;
        Trail.setBusy(submit, false);
      });
  });
})();
