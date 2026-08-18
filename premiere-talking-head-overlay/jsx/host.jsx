/*
 * Talking Head Overlay - ExtendScript host.
 *
 * ExtendScript is ES3: no JSON, no Array.forEach, no Array.indexOf. Everything
 * below sticks to that subset deliberately.
 *
 * Structure it builds, given a selected talking-head clip on track V(n):
 *
 *   V(n+2)  border graphic   - stroke in the chosen colour, transparent inside
 *   V(n+1)  matte graphic    - white silhouette, read by Track Matte Key
 *   V(n)    talking head     - Track Matte Key pointed at V(n+1)
 *   V(n-1)  whatever background you already had
 *
 * Effect and property lookups go by name with fallbacks, and every step logs
 * what it actually found. When something misbehaves on a specific Premiere
 * build, the panel's status pane should say which step and which name.
 */

var THO_LOG = [];
var THO_BIN = 'Talking Head Overlay';

function thoLog(m) { THO_LOG[THO_LOG.length] = String(m); }

/* -------------------------------------------------------------- JSON out  */

function thoQuote(s) {
    s = String(s);
    var out = '';
    for (var i = 0; i < s.length; i++) {
        var c = s.charAt(i);
        var cc = s.charCodeAt(i);
        if (c === '"') { out += '\\"'; }
        else if (c === '\\') { out += '\\\\'; }
        else if (cc < 32) { out += '\\u' + ('0000' + cc.toString(16)).slice(-4); }
        else { out += c; }
    }
    return '"' + out + '"';
}

function thoStringify(v) {
    var t = typeof v;
    if (v === null || v === undefined) { return 'null'; }
    if (t === 'number') { return isFinite(v) ? String(v) : 'null'; }
    if (t === 'boolean') { return v ? 'true' : 'false'; }
    if (t === 'string') { return thoQuote(v); }
    if (v instanceof Array) {
        var a = [];
        for (var i = 0; i < v.length; i++) { a[a.length] = thoStringify(v[i]); }
        return '[' + a.join(',') + ']';
    }
    var p = [];
    for (var k in v) {
        if (v.hasOwnProperty(k)) { p[p.length] = thoQuote(k) + ':' + thoStringify(v[k]); }
    }
    return '{' + p.join(',') + '}';
}

function thoOk(data) { return thoStringify({ ok: true, data: data, log: THO_LOG }); }

function thoErr(e) {
    var msg = (e && e.message) ? e.message : String(e);
    if (e && e.line) { msg += ' (host.jsx line ' + e.line + ')'; }
    return thoStringify({ ok: false, error: msg, log: THO_LOG });
}

/* ------------------------------------------------------------- lookups    */

function thoSeconds(t) {
    // Time objects expose .seconds; QE's expose .secs.
    if (t === null || t === undefined) { return 0; }
    if (t.seconds !== undefined) { return parseFloat(t.seconds); }
    if (t.secs !== undefined) { return parseFloat(t.secs); }
    return parseFloat(t);
}

function thoTime(seconds) {
    var t = new Time();
    t.seconds = seconds;
    return t;
}

function thoFindSelected(seq) {
    for (var t = 0; t < seq.videoTracks.numTracks; t++) {
        var track = seq.videoTracks[t];
        for (var c = 0; c < track.clips.numItems; c++) {
            if (track.clips[c].isSelected()) {
                return { clip: track.clips[c], trackIndex: t, clipIndex: c };
            }
        }
    }
    return null;
}

/** Match a component by displayName first, then matchName. */
function thoFindComponent(clip, names) {
    var comps = clip.components;
    for (var n = 0; n < names.length; n++) {
        for (var i = 0; i < comps.numItems; i++) {
            var c = comps[i];
            var dn = '';
            var mn = '';
            try { dn = String(c.displayName); } catch (e) {}
            try { mn = String(c.matchName); } catch (e2) {}
            if (dn === names[n] || mn === names[n]) { return c; }
        }
    }
    return null;
}

function thoFindProperty(comp, names) {
    var props = comp.properties;
    for (var n = 0; n < names.length; n++) {
        for (var i = 0; i < props.numItems; i++) {
            var dn = '';
            try { dn = String(props[i].displayName); } catch (e) {}
            if (dn === names[n]) { return props[i]; }
        }
    }
    return null;
}

function thoListProperties(comp) {
    var out = [];
    try {
        for (var i = 0; i < comp.properties.numItems; i++) {
            out[out.length] = String(comp.properties[i].displayName);
        }
    } catch (e) {}
    return out.join(', ');
}

/* ------------------------------------------------------------- context    */

function THO_getContext() {
    THO_LOG = [];
    try {
        var seq = app.project.activeSequence;
        if (!seq) { throw new Error('No active sequence. Open one in the timeline first.'); }

        var settings = seq.getSettings();
        var sel = thoFindSelected(seq);

        return thoOk({
            sequenceName: String(seq.name),
            width: parseInt(settings.videoFrameWidth, 10),
            height: parseInt(settings.videoFrameHeight, 10),
            videoTrackCount: seq.videoTracks.numTracks,
            projectPath: String(app.project.path || ''),
            hasSelection: sel !== null,
            selectedName: sel ? String(sel.clip.name) : '',
            selectedTrack: sel ? sel.trackIndex : -1,
            selectedStart: sel ? thoSeconds(sel.clip.start) : 0,
            selectedDuration: sel ? (thoSeconds(sel.clip.end) - thoSeconds(sel.clip.start)) : 0
        });
    } catch (e) {
        return thoErr(e);
    }
}

/* ------------------------------------------------------------- tracks     */

function thoEnsureVideoTracks(seq, needed) {
    if (seq.videoTracks.numTracks >= needed) { return; }
    var toAdd = needed - seq.videoTracks.numTracks;
    thoLog('Adding ' + toAdd + ' video track(s) to reach V' + needed + '.');
    try {
        app.enableQE();
        var qeSeq = qe.project.getActiveSequence();
        qeSeq.addTracks(toAdd, seq.videoTracks.numTracks, 0, 0);
    } catch (e) {
        throw new Error('Could not add video tracks (QE addTracks failed: ' + e.message +
                        '). Add ' + toAdd + ' video track(s) by hand and re-apply.');
    }
}

/* ------------------------------------------------------------- import     */

function thoFindOrCreateBin(name) {
    var root = app.project.rootItem;
    for (var i = 0; i < root.children.numItems; i++) {
        if (String(root.children[i].name) === name) { return root.children[i]; }
    }
    return root.createBin(name);
}

function thoBaseName(path) {
    var i = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
    return i < 0 ? path : path.substring(i + 1);
}

function thoImport(path) {
    var bin = thoFindOrCreateBin(THO_BIN);
    var base = thoBaseName(path);

    // Re-applying the same look reuses the PNG, so check the bin first.
    for (var i = 0; i < bin.children.numItems; i++) {
        if (String(bin.children[i].name) === base) {
            thoLog('Reusing already-imported ' + base + '.');
            return bin.children[i];
        }
    }

    var before = bin.children.numItems;
    if (!app.project.importFiles([path], true, bin, false)) {
        throw new Error('Premiere refused to import ' + path);
    }
    if (bin.children.numItems <= before) {
        throw new Error('Imported ' + base + ' but it did not land in the "' + THO_BIN + '" bin.');
    }
    thoLog('Imported ' + base + '.');
    return bin.children[bin.children.numItems - 1];
}

/* ------------------------------------------------------------- placement  */

function thoPlace(seq, trackIndex, projItem, startSec, durSec) {
    var track = seq.videoTracks[trackIndex];

    var placed = false;
    try {
        placed = track.overwriteClip(projItem, thoTime(startSec));
    } catch (e) {
        // Older builds want plain seconds rather than a Time object.
        try { placed = track.overwriteClip(projItem, startSec); } catch (e2) {
            throw new Error('overwriteClip failed on V' + (trackIndex + 1) + ': ' + e2.message);
        }
    }
    if (placed === false) {
        throw new Error('overwriteClip returned false on V' + (trackIndex + 1) +
                        '. Is that track locked?');
    }

    var clip = null;
    for (var i = 0; i < track.clips.numItems; i++) {
        if (Math.abs(thoSeconds(track.clips[i].start) - startSec) < 0.005) {
            clip = track.clips[i];
            break;
        }
    }
    if (!clip) {
        throw new Error('Placed a graphic on V' + (trackIndex + 1) + ' but could not find it again.');
    }

    // Stills come in at the default duration; stretch to match the head clip.
    try {
        clip.end = thoTime(startSec + durSec);
    } catch (e3) {
        thoLog('Could not set the out point on V' + (trackIndex + 1) + ': ' + e3.message);
    }
    return clip;
}

function thoSetPosition(clip, x, y) {
    var motion = thoFindComponent(clip, ['Motion', 'AE.ADBE Motion']);
    if (!motion) { thoLog('No Motion component on ' + clip.name + '; leaving it centred.'); return; }
    var pos = thoFindProperty(motion, ['Position']);
    if (!pos) { thoLog('No Position property on ' + clip.name + '.'); return; }
    pos.setValue([x, y], true);
}

/* ------------------------------------------------------------- matte key  */

function thoFindQEClip(qeTrack, startSec) {
    for (var i = 0; i < qeTrack.numItems; i++) {
        var item = qeTrack.getItemAt(i);
        try {
            if (String(item.type) !== 'Clip') { continue; }
        } catch (e) { /* some builds omit .type; fall through to the time check */ }
        try {
            if (Math.abs(thoSeconds(item.start) - startSec) < 0.005) { return item; }
        } catch (e2) {}
    }
    return null;
}

function thoApplyTrackMatte(seq, headTrackIndex, headClipStart, matteTrackIndex) {
    var track = seq.videoTracks[headTrackIndex];

    // Re-find the clip: QE and the standard DOM hand out separate references,
    // and the DOM one goes stale once QE touches the clip.
    function head() {
        for (var i = 0; i < track.clips.numItems; i++) {
            if (Math.abs(thoSeconds(track.clips[i].start) - headClipStart) < 0.005) {
                return track.clips[i];
            }
        }
        return null;
    }

    var clip = head();
    if (!clip) { throw new Error('Lost track of the talking-head clip on V' + (headTrackIndex + 1) + '.'); }

    var existing = thoFindComponent(clip, ['Track Matte Key']);
    if (existing) {
        thoLog('Track Matte Key already on this clip; updating it rather than stacking another.');
    } else {
        app.enableQE();
        var qeSeq = qe.project.getActiveSequence();
        var qeTrack = qeSeq.getVideoTrackAt(headTrackIndex);
        var qeClip = thoFindQEClip(qeTrack, headClipStart);
        if (!qeClip) {
            throw new Error('Could not reach the talking-head clip through QE to add the effect.');
        }
        var fx = qe.project.getVideoEffectByName('Track Matte Key');
        if (!fx) {
            throw new Error('No effect named "Track Matte Key". If Premiere is not running in ' +
                            'English, the effect name differs and this lookup needs your locale.');
        }
        qeClip.addVideoEffect(fx);
        thoLog('Applied Track Matte Key.');
        clip = head();
    }

    var comp = thoFindComponent(clip, ['Track Matte Key']);
    if (!comp) { throw new Error('Applied Track Matte Key but cannot read its parameters back.'); }
    thoLog('Track Matte Key params: ' + thoListProperties(comp));

    var matteProp = thoFindProperty(comp, ['Matte']);
    if (!matteProp) { throw new Error('Track Matte Key has no "Matte" parameter on this build.'); }

    // The dropdown is 0 = None, 1 = Video 1, 2 = Video 2 ... and our track
    // index is 0-based, so the value is one more than the index.
    var matteValue = matteTrackIndex + 1;
    matteProp.setValue(matteValue, true);
    thoLog('Matte source set to Video ' + matteValue + '.');

    var compositeProp = thoFindProperty(comp, ['Composite Using']);
    if (compositeProp) {
        compositeProp.setValue(0, true); // 0 = Matte Alpha
        thoLog('Composite Using set to Matte Alpha.');
    }

    return clip;
}

/* ------------------------------------------------------------- keyframes  */

function thoKey(prop, time, value) {
    prop.addKey(time);
    prop.setValueAtKey(time, value, true);
}

/**
 * Scale up from nothing, overshoot, settle; mirror it on the way out.
 * The overshoot keyframe is what sells the pop - it reads well even where
 * setInterpolationTypeAtKey is unavailable and the keys stay linear.
 */
function thoAnimateScale(clip, timeBase, dur, inDur, outDur, overshootPct) {
    var motion = thoFindComponent(clip, ['Motion', 'AE.ADBE Motion']);
    if (!motion) { thoLog('No Motion on ' + clip.name + '; skipping its animation.'); return; }
    var scale = thoFindProperty(motion, ['Scale']);
    if (!scale) { thoLog('No Scale on ' + clip.name + '; skipping its animation.'); return; }

    // Whatever framing is already on the clip becomes the settled value.
    var base = 100;
    try { base = parseFloat(scale.getValue()); } catch (e) {}
    if (!isFinite(base) || base <= 0) { base = 100; }
    var over = base * (overshootPct / 100);

    scale.setTimeVarying(true);

    if (inDur > 0) {
        thoKey(scale, timeBase, 0);
        thoKey(scale, timeBase + inDur * 0.62, over);
        thoKey(scale, timeBase + inDur, base);
    } else {
        thoKey(scale, timeBase, base);
    }

    if (outDur > 0 && dur > inDur + outDur) {
        thoKey(scale, timeBase + dur - outDur, base);
        thoKey(scale, timeBase + dur - outDur * 0.35, over * 0.98);
        thoKey(scale, timeBase + dur, 0);
    }

    // Bezier easing where the build supports it; linear is an acceptable
    // fallback given the overshoot already carries the motion.
    try {
        for (var i = 0; i < scale.getKeys().length; i++) {
            scale.setInterpolationTypeAtKey(scale.getKeys()[i], 5, true);
        }
    } catch (e2) {
        thoLog('Easing not applied (' + e2.message + '); keyframes are linear.');
    }

    thoLog('Animated Scale on ' + clip.name + ' (base ' + base + '%, peak ' +
           Math.round(over) + '%).');
}

/* ------------------------------------------------------------- apply      */

function THO_apply(jsonStr) {
    THO_LOG = [];
    try {
        var o = eval('(' + jsonStr + ')');

        var seq = app.project.activeSequence;
        if (!seq) { throw new Error('No active sequence.'); }

        var sel = thoFindSelected(seq);
        if (!sel) { throw new Error('Select the talking-head clip on the timeline, then apply.'); }

        var headTrack = sel.trackIndex;
        var start = thoSeconds(sel.clip.start);
        var dur = thoSeconds(sel.clip.end) - start;
        if (dur <= 0) { throw new Error('The selected clip has no duration.'); }
        thoLog('Head clip "' + sel.clip.name + '" on V' + (headTrack + 1) +
               ' at ' + start.toFixed(3) + 's for ' + dur.toFixed(3) + 's.');

        var matteTrack = headTrack + 1;
        var borderTrack = headTrack + 2;
        thoEnsureVideoTracks(seq, borderTrack + 1);
        seq = app.project.activeSequence; // re-fetch: the collection changed

        var matteItem = thoImport(o.mattePath);
        var borderItem = thoImport(o.borderPath);

        var matteClip = thoPlace(seq, matteTrack, matteItem, start, dur);
        var borderClip = thoPlace(seq, borderTrack, borderItem, start, dur);
        thoSetPosition(matteClip, o.posX, o.posY);
        thoSetPosition(borderClip, o.posX, o.posY);
        thoLog('Placed matte on V' + (matteTrack + 1) + ' and border on V' + (borderTrack + 1) + '.');

        var headClip = thoApplyTrackMatte(seq, headTrack, start, matteTrack);

        if (o.inDur > 0 || o.outDur > 0) {
            // Keyframe times are measured from the sequence start on some
            // builds and from the clip start on others; the panel exposes the
            // switch because there is no reliable way to detect which.
            var timeBase = o.clipTimeBase ? 0 : start;
            thoLog('Keyframe time base: ' + (o.clipTimeBase ? 'clip-relative' : 'sequence') +
                   ' (first key at ' + timeBase.toFixed(3) + 's).');
            thoAnimateScale(matteClip, timeBase, dur, o.inDur, o.outDur, o.overshoot);
            thoAnimateScale(borderClip, timeBase, dur, o.inDur, o.outDur, o.overshoot);
            if (o.animateHead && headClip) {
                thoAnimateScale(headClip, timeBase, dur, o.inDur, o.outDur, o.overshoot);
            }
        }

        return thoOk({
            headTrack: headTrack,
            matteTrack: matteTrack,
            borderTrack: borderTrack
        });
    } catch (e) {
        return thoErr(e);
    }
}
