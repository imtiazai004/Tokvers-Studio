/**
 * Contact — opens a pre-filled email from the form (no backend needed).
 * Reuses the global .an-rise reveal system. Requires: contact.css
 */
(function () {
  var form = document.getElementById('ctForm');
  if (!form) return;

  var TO = 'info@thetokverse.com';

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var name = (document.getElementById('ctName') || {}).value || '';
    var email = (document.getElementById('ctEmail') || {}).value || '';
    var msg = (document.getElementById('ctMsg') || {}).value || '';
    var subject = 'AIGC Automated enquiry' + (name ? ' — ' + name : '');
    var body =
      'Name: ' + name + '\r\n' +
      'Email: ' + email + '\r\n\r\n' +
      msg + '\r\n';
    window.location.href = 'mailto:' + TO +
      '?subject=' + encodeURIComponent(subject) +
      '&body=' + encodeURIComponent(body);
  });
})();
