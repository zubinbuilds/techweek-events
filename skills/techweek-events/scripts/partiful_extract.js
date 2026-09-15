// Run this in the page context of a Partiful event page (partiful.com/e/<id>)
// with a browser JavaScript tool. Returns a JSON string with the event's
// structured data and the viewer's login/RSVP state. No network calls; it only
// reads what the page already rendered.
//
// Works because Partiful is a Next.js app that embeds the event record in the
// __NEXT_DATA__ script tag (props.pageProps.event). The signed-in viewer's own
// state is NOT in that server-rendered blob (pageProps.guest is null even when
// logged in), so login/RSVP status is read from the rendered DOM instead.
(function () {
  try {
    var nd = JSON.parse(document.getElementById('__NEXT_DATA__').textContent);
    var pp = nd.props.pageProps || {};
    var e = pp.event || {};
    var q = (e.questionnaire || {}).questions || [];
    var links = Array.prototype.slice.call(document.querySelectorAll('a[href]'));
    var loggedIn = links.some(function (a) { return /^\/u\//.test(a.getAttribute('href') || ''); });
    var buttons = Array.prototype.slice.call(document.querySelectorAll('button'))
      .map(function (b) { return (b.innerText || '').replace(/\s+/g, ' ').trim(); })
      .filter(Boolean);
    var text = (document.body.innerText || '').replace(/\s+/g, ' ');
    var myStatus = null;
    if (/you'?re going|you are going/i.test(text) || buttons.some(function (b) { return /^going/i.test(b); })) myStatus = 'going';
    else if (buttons.some(function (b) { return /pending/i.test(b); })) myStatus = 'pending';
    else if (buttons.some(function (b) { return /waitlist/i.test(b); })) myStatus = 'waitlist';
    else if (/response was recorded/i.test(text)) myStatus = 'submitted';
    return JSON.stringify({
      id: e.id,
      title: e.title,
      hosts: (pp.hosts || []).map(function (h) { return h.name || h.displayName; }),
      description: e.description,
      start: e.startDate,
      end: e.endDate,
      timezone: e.timezone,
      neighborhood: (e.locationInfo || {}).neighborhood,
      approximateLocation: ((e.locationInfo || {}).mapsInfo || {}).approximateLocation,
      visibility: e.visibility,
      guestAction: e.guestAction,          // "RSVP" | "APPLY"
      ticketed: !!e.ticketing,             // paid tickets via Partiful -> agent must stop, user pays
      ticketButton: buttons.find(function (b) { return /^get tickets/i.test(b); }) || null,
      status: e.status,                    // "PUBLISHED" etc.
      rsvpsEnabled: e.rsvpsEnabled,
      isCapped: e.isCapped,
      atCapacity: e.atCapacity,
      maxCapacity: e.maxCapacity,
      goingGuestCount: e.goingGuestCount,
      questionnaireEnabled: e.questionnaireEnabled,
      hostQuestions: q.map(function (x) { return { id: x.id, text: x.text, type: x.type, required: !!x.required, options: x.options || null }; }),
      publicShortUrl: e.publicShortUrl,
      url: location.href,
      viewer: { loggedIn: loggedIn, rsvpStatus: myStatus, visibleButtons: buttons.slice(0, 20) }
    });
  } catch (err) {
    return JSON.stringify({ error: String(err), url: location.href, title: document.title });
  }
})();
