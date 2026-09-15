// Fill Partiful's "Questions from the hosts" form from a label -> answer map.
//
// Run in the page context AFTER the questionnaire dialog is open (you clicked
// the RSVP button, then Continue). Edit ANSWERS below, or build the array
// dynamically from the user's profile before executing.
//
// Why JS instead of the accessibility tree: Partiful's inputs have no
// name/id/aria-label, so accessibility refs are just "textbox", "textbox",
// "textbox"... and some tools only expose the first few. Each input's label is
// the nearest ancestor's first text line ("Company Website *"), so match on
// that. Values are set through the native setter + an "input" event so React
// registers them (a plain .value = "..." assignment is ignored by React).
//
// Returns a JSON report: one entry per input with {label, filled, value}.
// Anything with filled:false is a question you don't have an answer for —
// if its label ends with "*" it's required: stop and ask the user.
//
// Selects ("Select..." buttons) are not filled here: click the button, then
// click the option by text. Checkboxes: click them.
(function () {
  var ANSWERS = [
    // [label fragment (lowercase), answer] — first match wins, most specific first
    ['first name', 'FIRST'],
    ['last name', 'LAST'],
    ['company email', 'WORK_EMAIL'],
    ['email', 'EMAIL'],
    ['linkedin', 'LINKEDIN_URL'],
    ['github', 'GITHUB_URL'],
    ['job title', 'TITLE'],
    ['title', 'TITLE'],
    ['company website', 'WEBSITE'],
    ['website', 'WEBSITE'],
    ['company name', 'COMPANY'],
    ['what company', 'COMPANY'],
    ['organization', 'COMPANY'],
    ['company', 'COMPANY'],
    ['who referred', 'Found it on the Tech Week calendar'],
    ['how did you hear', 'Tech Week calendar'],
    ['dietary', 'No dietary restrictions'],
    ['phone', 'PHONE'],
    ['city', 'San Francisco'],
    ['name', 'FIRST LAST'],
  ];

  function labelOf(inp) {
    var el = inp;
    for (var k = 0; k < 6 && el; k++) {
      el = el.parentElement;
      if (!el) break;
      var t = (el.innerText || '').split('\n')[0].trim();
      if (t && t.length < 120) return t;
    }
    return '';
  }
  var setInput = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  var setArea = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  var report = [];
  Array.prototype.slice.call(document.querySelectorAll('input:not([type=checkbox]):not([type=radio]), textarea')).forEach(function (inp) {
    var label = labelOf(inp);
    var lab = label.toLowerCase();
    var hit = null;
    for (var i = 0; i < ANSWERS.length; i++) {
      if (lab.indexOf(ANSWERS[i][0]) !== -1) { hit = ANSWERS[i]; break; }
    }
    if (!hit || /^[A-Z_ ]+$/.test(hit[1])) {   // no answer, or a placeholder you forgot to replace
      report.push({ label: label, required: /\*\s*$/.test(label), filled: false });
      return;
    }
    (inp.tagName === 'TEXTAREA' ? setArea : setInput).call(inp, hit[1]);
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    inp.dispatchEvent(new Event('change', { bubbles: true }));
    report.push({ label: label, required: /\*\s*$/.test(label), filled: true, value: inp.value });
  });
  var selects = Array.prototype.slice.call(document.querySelectorAll('button'))
    .filter(function (b) { return /^select/i.test((b.innerText || '').trim()); })
    .map(function (b) { return labelOf(b); });
  return JSON.stringify({ inputs: report, selectsToClick: selects });
})();
