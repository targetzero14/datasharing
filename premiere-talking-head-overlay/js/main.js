/* Panel logic: read the sequence, draw the preview, write the PNGs, call the host. */

(function () {
  'use strict';

  var cs = new CSInterface();
  var isWin = cs.isWindows();
  var SEP = isWin ? '\\' : '/';

  // Filled in from the host on load / refresh.
  var ctx = { ready: false, width: 1920, height: 1080 };

  var el = {};
  [
    'context', 'preview', 'status', 'apply', 'refresh', 'advanced',
    'width', 'height', 'radius', 'posX', 'posY',
    'borderWidth', 'borderColor', 'borderHex', 'shadow',
    'inDur', 'outDur', 'overshoot', 'animateHead',
    'clipTimeBase', 'keepAssets'
  ].forEach(function (id) { el[id] = document.getElementById(id); });

  /* ---------------------------------------------------------------- status */

  function log(msg, cls) {
    var line = document.createElement('span');
    if (cls) line.className = cls;
    line.textContent = msg + '\n';
    el.status.appendChild(line);
    el.status.scrollTop = el.status.scrollHeight;
  }

  function clearLog() { el.status.textContent = ''; }

  function setContext(msg, cls) {
    el.context.textContent = msg;
    el.context.className = 'context' + (cls ? ' ' + cls : '');
  }

  /* ------------------------------------------------------------ host calls */

  function callHost(fn, payload, cb) {
    // JSON.stringify twice: once for the payload, once to make it a valid
    // JS string literal inside the ExtendScript expression we're building.
    var arg = payload === undefined ? '' : JSON.stringify(JSON.stringify(payload));
    cs.evalScript(fn + '(' + arg + ')', function (raw) {
      var res;
      try {
        res = JSON.parse(raw);
      } catch (e) {
        cb({ ok: false, error: 'Host script did not return JSON: ' + raw, log: [] });
        return;
      }
      cb(res);
    });
  }

  function dumpHostLog(res) {
    (res.log || []).forEach(function (l) { log('  ' + l); });
  }

  /* --------------------------------------------------------------- options */

  function options() {
    return {
      width: +el.width.value,
      height: +el.height.value,
      radius: +el.radius.value,
      borderWidth: +el.borderWidth.value,
      borderColor: el.borderColor.value,
      shadow: +el.shadow.value,
      centerX: +el.posX.value / 100,
      centerY: +el.posY.value / 100
    };
  }

  /* --------------------------------------------------------------- preview */

  function draw() {
    var o = options();
    // Fit the frame to the panel width, capped so it stays legible.
    var target = Math.max(220, Math.min(el.preview.parentElement.clientWidth || 320, 520));
    Shapes.renderPreview(el.preview, o, ctx, target / ctx.width);
  }

  function syncOutputs() {
    document.getElementById('widthOut').value = el.width.value;
    document.getElementById('heightOut').value = el.height.value;
    document.getElementById('radiusOut').value = el.radius.value;
    document.getElementById('posXOut').value = el.posX.value + '%';
    document.getElementById('posYOut').value = el.posY.value + '%';
    document.getElementById('borderWidthOut').value = el.borderWidth.value;
    document.getElementById('shadowOut').value = el.shadow.value;
    document.getElementById('inDurOut').value = (+el.inDur.value).toFixed(2) + 's';
    document.getElementById('outDurOut').value = (+el.outDur.value).toFixed(2) + 's';
    document.getElementById('overshootOut').value = el.overshoot.value + '%';
  }

  function update() {
    syncOutputs();
    draw();
  }

  /* ----------------------------------------------------------------- files */

  function ensureDir(dir) {
    // cep.fs.makedir only creates one level, so walk the path.
    var parts = dir.split(SEP);
    var path = isWin ? parts.shift() : ''; // drive letter, or POSIX root
    for (var i = 0; i < parts.length; i++) {
      if (!parts[i]) continue;
      path += SEP + parts[i];
      if (window.cep.fs.stat(path).err) {
        window.cep.fs.makedir(path);
      }
    }
    return dir;
  }

  function assetDir() {
    var base;
    if (ctx.projectPath) {
      base = ctx.projectPath.substring(0, ctx.projectPath.lastIndexOf(SEP));
    } else {
      base = cs.getSystemPath(SystemPath.USER_DATA);
    }
    return ensureDir(base + SEP + 'Talking Head Overlay');
  }

  /** Short stable key so the same look reuses the same PNG instead of piling up. */
  function lookKey(o) {
    var s = [o.width, o.height, o.radius, o.borderWidth, o.borderColor, o.shadow].join('_');
    var h = 0;
    for (var i = 0; i < s.length; i++) {
      h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    }
    return (h >>> 0).toString(36);
  }

  function writePng(path, canvas) {
    var res = window.cep.fs.writeFile(path, Shapes.toBase64(canvas), window.cep.encoding.Base64);
    if (res.err) throw new Error('Could not write ' + path + ' (cep.fs error ' + res.err + ')');
    return path;
  }

  /* ----------------------------------------------------------------- apply */

  function apply() {
    clearLog();
    if (!ctx.ready) {
      log('No sequence context yet - hit Refresh.', 'e');
      return;
    }

    el.apply.disabled = true;
    var o = options();

    var mattePath, borderPath;
    try {
      var dir = assetDir();
      var key = lookKey(o);
      mattePath = dir + SEP + 'tho-matte-' + key + '.png';
      borderPath = dir + SEP + 'tho-border-' + key + '.png';
      writePng(mattePath, Shapes.renderMatte(o));
      writePng(borderPath, Shapes.renderBorder(o));
      log('Wrote artwork to ' + dir, 's');
    } catch (e) {
      log('Failed writing artwork: ' + e.message, 'e');
      el.apply.disabled = false;
      return;
    }

    var size = Shapes.canvasSize(o);
    var payload = {
      mattePath: mattePath,
      borderPath: borderPath,
      // Premiere's Motion Position is normalised, 0.5/0.5 = frame centre.
      posX: o.centerX,
      posY: o.centerY,
      graphicWidth: size.w,
      graphicHeight: size.h,
      inDur: +el.inDur.value,
      outDur: +el.outDur.value,
      overshoot: +el.overshoot.value,
      animateHead: el.animateHead.checked,
      clipTimeBase: el.clipTimeBase.checked
    };

    callHost('THO_apply', payload, function (res) {
      el.apply.disabled = false;
      dumpHostLog(res);
      if (!res.ok) {
        log('FAILED: ' + res.error, 'e');
        return;
      }
      log('Done. Head on V' + (res.data.headTrack + 1) +
          ', matte on V' + (res.data.matteTrack + 1) +
          ', border on V' + (res.data.borderTrack + 1) + '.', 's');
      refresh();
    });
  }

  /* --------------------------------------------------------------- refresh */

  function refresh() {
    callHost('THO_getContext', undefined, function (res) {
      if (!res.ok) {
        ctx.ready = false;
        setContext(res.error, 'err');
        return;
      }
      var d = res.data;
      ctx = {
        ready: true,
        width: d.width,
        height: d.height,
        projectPath: d.projectPath
      };

      // Keep the sliders meaningful for this frame size.
      el.width.max = d.width;
      el.height.max = d.height;
      el.radius.max = Math.round(Math.min(+el.width.value, +el.height.value) / 2);

      if (d.hasSelection) {
        setContext(d.sequenceName + '  ' + d.width + '×' + d.height + '\n' +
                   'Selected: ' + d.selectedName + ' on V' + (d.selectedTrack + 1) +
                   '  (' + d.selectedDuration.toFixed(2) + 's)', 'ok');
      } else {
        setContext(d.sequenceName + '  ' + d.width + '×' + d.height + '\n' +
                   'Select the talking-head clip on the timeline.', 'warn');
      }
      draw();
    });
  }

  /* ---------------------------------------------------------------- wiring */

  ['width', 'height', 'radius', 'posX', 'posY', 'borderWidth', 'shadow',
   'inDur', 'outDur', 'overshoot'].forEach(function (id) {
    el[id].addEventListener('input', function () {
      if (id === 'width' || id === 'height') {
        el.radius.max = Math.round(Math.min(+el.width.value, +el.height.value) / 2);
        if (+el.radius.value > +el.radius.max) el.radius.value = el.radius.max;
      }
      update();
    });
  });

  el.borderColor.addEventListener('input', function () {
    el.borderHex.value = el.borderColor.value;
    draw();
  });

  el.borderHex.addEventListener('change', function () {
    var v = el.borderHex.value.trim();
    if (!/^#?[0-9a-fA-F]{6}$/.test(v)) {
      el.borderHex.value = el.borderColor.value;
      return;
    }
    if (v.charAt(0) !== '#') v = '#' + v;
    el.borderColor.value = v.toLowerCase();
    el.borderHex.value = v.toLowerCase();
    draw();
  });

  document.querySelectorAll('[data-preset]').forEach(function (b) {
    b.addEventListener('click', function () {
      var side = Math.min(+el.width.value, +el.height.value);
      switch (b.dataset.preset) {
        case 'circle':
          el.width.value = side; el.height.value = side;
          el.radius.value = side / 2;
          break;
        case 'squircle':
          el.width.value = side; el.height.value = side;
          el.radius.value = Math.round(side * 0.28);
          break;
        case 'card':
          el.height.value = Math.round(+el.width.value * 0.62);
          el.radius.value = 24;
          break;
        case 'square':
          el.width.value = side; el.height.value = side;
          el.radius.value = 0;
          break;
      }
      el.radius.max = Math.round(Math.min(+el.width.value, +el.height.value) / 2);
      update();
    });
  });

  document.querySelectorAll('[data-corner]').forEach(function (b) {
    b.addEventListener('click', function () {
      // Inset far enough that the shape and its border clear the frame edge.
      var mx = (+el.width.value / 2 + 60) / ctx.width * 100;
      var my = (+el.height.value / 2 + 60) / ctx.height * 100;
      var map = {
        tl: [mx, my], tr: [100 - mx, my], c: [50, 50],
        bl: [mx, 100 - my], br: [100 - mx, 100 - my]
      };
      var p = map[b.dataset.corner];
      el.posX.value = Math.max(0, Math.min(100, p[0])).toFixed(1);
      el.posY.value = Math.max(0, Math.min(100, p[1])).toFixed(1);
      update();
    });
  });

  el.advanced.querySelector('.toggle').addEventListener('click', function () {
    el.advanced.classList.toggle('collapsed');
  });

  el.apply.addEventListener('click', apply);
  el.refresh.addEventListener('click', function () { clearLog(); refresh(); });
  window.addEventListener('resize', draw);

  update();
  refresh();
})();
