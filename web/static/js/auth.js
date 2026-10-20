/* Sign-in and sign-up screens: inline validation, show/hide password,
   one-click demo sign-in, and the post-login redirect. */
(function () {
  'use strict';

  var Trail = window.Trail;

  document.querySelectorAll('[data-toggle-password]').forEach(function (button) {
    button.addEventListener('click', function () {
      var input = document.getElementById(button.getAttribute('data-toggle-password'));
      if (!input) return;
      var showing = input.getAttribute('type') === 'text';
      input.setAttribute('type', showing ? 'password' : 'text');
      button.textContent = showing ? 'Show' : 'Hide';
      button.setAttribute('aria-pressed', showing ? 'false' : 'true');
      input.focus();
    });
  });

  function redirectTarget(form) {
    var next = form.getAttribute('data-next') || '/';
    return next.charAt(0) === '/' && next.indexOf('//') !== 0 ? next : '/';
  }

  var EMAIL_RE = /^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$/;

  function loginForm() {
    var form = document.getElementById('login-form');
    if (!form) return;

    var email = form.querySelector('[name="email"]');
    var password = form.querySelector('[name="password"]');
    var submit = form.querySelector('button[type="submit"]');
    var submitting = false;

    function validate() {
      var errors = {};
      if (!email.value.trim()) errors.email = 'Enter your email or username.';
      if (!password.value) errors.password = 'Enter your password.';
      return errors;
    }

    function send() {
      if (submitting) return;
      var errors = validate();
      if (Object.keys(errors).length) {
        Trail.setErrors(form, errors);
        return;
      }
      submitting = true;
      Trail.setErrors(form, {});
      Trail.setBusy(submit, true);
      Trail.api('/api/auth/login', {
        method: 'POST',
        body: { email: email.value.trim(), password: password.value },
      })
        .then(function () {
          window.location.assign(redirectTarget(form));
        })
        .catch(function (error) {
          submitting = false;
          Trail.setBusy(submit, false);
          if (error.fields && Object.keys(error.fields).length) {
            Trail.setErrors(form, error.fields, error.message);
          } else {
            Trail.setErrors(form, {}, error.message);
          }
          if (error.status === 401 || error.status === 429) password.focus();
        });
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      send();
    });

    var demo = document.querySelector('[data-demo-fill]');
    if (demo) {
      demo.addEventListener('click', function () {
        email.value = 'cenius@cenius.ai';
        password.value = 'cenius';
        send();
      });
    }
  }

  function signupForm() {
    var form = document.getElementById('signup-form');
    if (!form) return;

    var name = form.querySelector('[name="display_name"]');
    var email = form.querySelector('[name="email"]');
    var password = form.querySelector('[name="password"]');
    var confirm = form.querySelector('[name="password_confirm"]');
    var submit = form.querySelector('button[type="submit"]');
    var submitting = false;

    function validate() {
      var errors = {};
      if (name.value.trim().length < 2) errors.display_name = 'Enter your name (2 characters or more).';
      if (!EMAIL_RE.test(email.value.trim())) errors.email = 'Enter an email address like name@example.com.';
      if (password.value.length < 8) errors.password = 'Use at least 8 characters for your password.';
      if (confirm.value !== password.value) errors.password_confirm = 'The two passwords do not match.';
      return errors;
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
      Trail.api('/api/auth/register', {
        method: 'POST',
        body: {
          display_name: name.value.trim(),
          email: email.value.trim(),
          password: password.value,
          password_confirm: confirm.value,
        },
      })
        .then(function () {
          window.location.assign(redirectTarget(form));
        })
        .catch(function (error) {
          submitting = false;
          Trail.setBusy(submit, false);
          Trail.setErrors(form, error.fields || {}, error.message);
        });
    });
  }

  if (Trail) {
    loginForm();
    signupForm();
  }
})();
