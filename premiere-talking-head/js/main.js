/* Talking Head Toolkit — panel logic */
(function () {
  'use strict';

  var cs = new CSInterface();

  var state = {
    corner: 'br',
    sizePct: 33
  };

  // ---- element refs ----
  var cornerGrid = document.getElementById('cornerGrid');
  var sizeSeg = document.getElementById('sizeSeg');
  var marginEl = document.getElementById('margin');
  var marginVal = document.getElementById('marginVal');
  var animInEl = document.getElementById('animIn');
  var durationEl = document.getElementById('duration');
  var durationVal = document.getElementById('durationVal');
  var animOutEl = document.getElementById('animOut');
  var dropShadowEl = document.getElementById('dropShadow');
  var applyBtn = document.getElementById('applyBtn');
  var resetBtn = document.getElementById('resetBtn');
  var statusEl = document.getElementById('status');

  // ---- pickers ----
  function bindSegmented(container, dataAttr, onPick) {
    container.addEventListener('click', function (e) {
      var btn = e.target.closest('button');
      if (!btn) return;
      var buttons = container.querySelectorAll('button');
      for (var i = 0; i < buttons.length; i++) buttons[i].classList.remove('active');
      btn.classList.add('active');
      onPick(btn.getAttribute(dataAttr));
    });
  }

  bindSegmented(cornerGrid, 'data-corner', function (v) { state.corner = v; });
  bindSegmented(sizeSeg, 'data-size', function (v) { state.sizePct = parseInt(v, 10); });

  marginEl.addEventListener('input', function () {
    marginVal.textContent = marginEl.value + '%';
  });
  durationEl.addEventListener('input', function () {
    durationVal.textContent = parseFloat(durationEl.value).toFixed(1) + 's';
  });

  // ---- host bridge ----
  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = 'status' + (kind ? ' ' + kind : '');
  }

  function callHost(fnCall) {
    setStatus('Working…');
    cs.evalScript(fnCall, function (result) {
      var res;
      try {
        res = JSON.parse(result);
      } catch (e) {
        // ExtendScript runtime errors come back as plain strings
        setStatus('Premiere error: ' + result, 'error');
        return;
      }
      setStatus(res.message, res.ok ? 'ok' : 'error');
    });
  }

  applyBtn.addEventListener('click', function () {
    var params = {
      corner: state.corner,
      sizePct: state.sizePct,
      marginPct: parseInt(marginEl.value, 10),
      animIn: animInEl.value,
      animOut: animOutEl.checked,
      durationSec: parseFloat(durationEl.value),
      dropShadow: dropShadowEl.checked
    };
    // Pass params as a quoted JSON string argument to the host function.
    var arg = JSON.stringify(JSON.stringify(params));
    callHost('THT_applyOverlay(' + arg + ')');
  });

  resetBtn.addEventListener('click', function () {
    callHost('THT_reset()');
  });

  // initial readiness check
  callHost('THT_status()');
})();
