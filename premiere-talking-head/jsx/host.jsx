/**
 * Talking Head Toolkit — Premiere Pro host script (ExtendScript)
 *
 * Applies picture-in-picture "talking head" overlay layouts and simple
 * intro/outro animations (slide, pop, fade) to the selected video clip
 * in the active sequence, by keyframing the Motion (Position/Scale) and
 * Opacity components.
 *
 * Notes on the Premiere scripting model used here:
 *  - Component keyframe times are expressed in seconds relative to the
 *    clip's SOURCE media, so every keyframe is offset by clip.inPoint.
 *  - Position is normalized: (0.5, 0.5) is the center of the sequence
 *    frame; (0,0) is the top-left. The clip's anchor point is its center.
 *  - Scale is a percentage of the source size. Size presets assume the
 *    camera source matches the sequence resolution; a correction factor
 *    is computed from the source width when it is available.
 */

// ---------------------------------------------------------------------------
// small utilities (ExtendScript is ES3 — no JSON, no Array.prototype extras)
// ---------------------------------------------------------------------------

function THT_quote(s) {
    return '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n') + '"';
}

function THT_ok(msg) {
    return '{"ok":true,"message":' + THT_quote(msg) + '}';
}

function THT_err(msg) {
    return '{"ok":false,"message":' + THT_quote(msg) + '}';
}

// Temporal interpolation constants (from the Premiere Pro scripting API).
var THT_INTERP_LINEAR = 1;
var THT_INTERP_BEZIER = 6;

// ---------------------------------------------------------------------------
// selection helpers
// ---------------------------------------------------------------------------

function THT_getSelectedVideoClip() {
    var seq = app.project.activeSequence;
    if (!seq) {
        return { error: 'No active sequence. Open a sequence first.' };
    }
    var sel;
    try {
        sel = seq.getSelection();
    } catch (e) {
        sel = null;
    }
    if (!sel || sel.length === 0) {
        return { error: 'Nothing selected. Select your talking-head clip in the timeline.' };
    }
    for (var i = 0; i < sel.length; i++) {
        var item = sel[i];
        // mediaType is "Video" for video clips; audio halves report "Audio".
        if (item && item.mediaType && String(item.mediaType) === 'Video') {
            return { seq: seq, clip: item };
        }
    }
    return { error: 'Selection contains no video clip. Select the camera/talking-head video clip.' };
}

function THT_findComponent(clip, matchNames) {
    var comps = clip.components;
    if (!comps) return null;
    for (var i = 0; i < comps.numItems; i++) {
        var c = comps[i];
        for (var j = 0; j < matchNames.length; j++) {
            if (c.matchName === matchNames[j] || c.displayName === matchNames[j]) {
                return c;
            }
        }
    }
    return null;
}

function THT_findParam(component, displayNames) {
    if (!component) return null;
    var props = component.properties;
    for (var i = 0; i < props.numItems; i++) {
        var p = props[i];
        for (var j = 0; j < displayNames.length; j++) {
            if (p.displayName === displayNames[j]) {
                return p;
            }
        }
    }
    return null;
}

// Reset a param to a static (non-keyframed) state so stale keyframes from a
// previous run never linger.
function THT_clearKeys(param) {
    try {
        param.setTimeVarying(false);
    } catch (e) {}
}

function THT_addKey(param, timeSecs, value, interp) {
    param.addKey(timeSecs);
    param.setValueAtKey(timeSecs, value, 1);
    if (interp !== undefined) {
        try {
            param.setInterpolationTypeAtKey(timeSecs, interp, 1);
        } catch (e) {
            // Older builds may not support this; linear fallback is fine.
        }
    }
}

// Position is a 2-value param; setValueAtKey expects an array.
function THT_addKey2D(param, timeSecs, x, y, interp) {
    param.addKey(timeSecs);
    param.setValueAtKey(timeSecs, [x, y], 1);
    if (interp !== undefined) {
        try {
            param.setInterpolationTypeAtKey(timeSecs, interp, 1);
        } catch (e) {}
    }
}

// ---------------------------------------------------------------------------
// geometry
// ---------------------------------------------------------------------------

/**
 * Compute the overlay's final center position (normalized 0..1) and the
 * off-screen start position for slide animations.
 *
 * corner: "tl" | "tr" | "bl" | "br" | "center"
 * widthFrac / heightFrac: overlay size as a fraction of the sequence frame
 * marginFrac: gap between overlay edge and frame edge, as fraction of width
 */
function THT_layout(corner, widthFrac, heightFrac, marginFrac) {
    var halfW = widthFrac / 2;
    var halfH = heightFrac / 2;
    var m = marginFrac;

    var x, y, offX, offY;

    if (corner === 'center') {
        x = 0.5; y = 0.5;
        offX = 0.5; offY = 1 + halfH; // slides up from bottom
    } else {
        var left = (corner === 'tl' || corner === 'bl');
        var top = (corner === 'tl' || corner === 'tr');
        x = left ? (m + halfW) : (1 - m - halfW);
        y = top ? (m + halfH) : (1 - m - halfH);
        // slide in horizontally from the nearest vertical edge
        offX = left ? (-halfW - 0.02) : (1 + halfW + 0.02);
        offY = y;
    }
    return { x: x, y: y, offX: offX, offY: offY };
}

// ---------------------------------------------------------------------------
// drop shadow via QE DOM (best effort)
// ---------------------------------------------------------------------------

function THT_applyDropShadow(seq, clip) {
    try {
        app.enableQE();
        var qeSeq = qe.project.getActiveSequence();
        if (!qeSeq) return 'QE: no active sequence';

        var clipStartTicks = String(clip.start.ticks);
        var fx = qe.project.getVideoEffectByName('Drop Shadow');
        if (!fx) return 'QE: Drop Shadow effect not found';

        for (var t = 0; t < qeSeq.numVideoTracks; t++) {
            var track = qeSeq.getVideoTrackAt(t);
            for (var i = 0; i < track.numItems; i++) {
                var item = track.getItemAt(i);
                if (!item || item.type === 'Empty') continue;
                if (item.start && String(item.start.ticks) === clipStartTicks &&
                    item.name === clip.name) {
                    item.addVideoEffect(fx);
                    return '';
                }
            }
        }
        return 'QE: could not locate the clip on any video track';
    } catch (e) {
        return 'QE: ' + e.toString();
    }
}

// ---------------------------------------------------------------------------
// main entry point, called from the panel
// ---------------------------------------------------------------------------

/**
 * paramsStr is a JSON object literal produced by the panel:
 * {
 *   corner:      "br" | "bl" | "tr" | "tl" | "center",
 *   sizePct:     30,          // overlay width as % of frame width
 *   marginPct:   4,           // margin as % of frame width
 *   animIn:      "none" | "slide" | "pop" | "fade" | "slidefade",
 *   animOut:     true|false,  // mirror the animation at the clip's end
 *   durationSec: 0.5,
 *   dropShadow:  true|false
 * }
 */
function THT_applyOverlay(paramsStr) {
    var p;
    try {
        p = eval('(' + paramsStr + ')'); // panel-controlled input only
    } catch (e) {
        return THT_err('Bad parameters: ' + e.toString());
    }

    var found = THT_getSelectedVideoClip();
    if (found.error) return THT_err(found.error);
    var seq = found.seq;
    var clip = found.clip;

    var motion = THT_findComponent(clip, ['AE.ADBE Motion', 'Motion']);
    var opacityComp = THT_findComponent(clip, ['AE.ADBE Opacity', 'Opacity']);
    if (!motion) return THT_err('Could not find the Motion component on the selected clip.');

    var posParam = THT_findParam(motion, ['Position']);
    var scaleParam = THT_findParam(motion, ['Scale']);
    var opacityParam = THT_findParam(opacityComp, ['Opacity']);
    if (!posParam || !scaleParam) {
        return THT_err('Could not find Position/Scale on the Motion component.');
    }

    // ---- size ------------------------------------------------------------
    // Target: overlay occupies sizePct% of the sequence width. Scale is
    // relative to the source, so correct for source vs. sequence width when
    // the source resolution is reported.
    var seqW = 1920, seqH = 1080;
    try {
        seqW = seq.frameSizeHorizontal;
        seqH = seq.frameSizeVertical;
    } catch (e) {}

    var srcW = seqW, srcH = seqH;
    try {
        // videoInfo not exposed everywhere; getFootageInterpretation is safer
        var interp = clip.projectItem.getFootageInterpretation();
        if (interp && interp.frameRect && interp.frameRect.width > 0) {
            srcW = interp.frameRect.width;
            srcH = interp.frameRect.height;
        }
    } catch (e) {}

    var sizePct = (typeof p.sizePct === 'number' && p.sizePct > 0) ? p.sizePct : 30;
    var targetScale = sizePct * (seqW / srcW); // % scale so width = sizePct% of frame
    var widthFrac = sizePct / 100;
    var heightFrac = widthFrac * ((srcH / srcW) / (seqH / seqW));

    var marginFrac = ((typeof p.marginPct === 'number') ? p.marginPct : 4) / 100;
    var L = THT_layout(p.corner || 'br', widthFrac, heightFrac, marginFrac);

    // ---- timing ----------------------------------------------------------
    var d = (typeof p.durationSec === 'number' && p.durationSec > 0.05) ? p.durationSec : 0.5;
    var tIn = clip.inPoint.seconds;                  // source-relative clip start
    var clipLen = clip.outPoint.seconds - clip.inPoint.seconds;
    if (d * (p.animOut ? 2.5 : 1.2) > clipLen) {
        d = Math.max(0.1, clipLen / (p.animOut ? 3 : 2));
    }
    var tOutEnd = clip.outPoint.seconds;
    var anim = p.animIn || 'none';

    // ---- apply -----------------------------------------------------------
    THT_clearKeys(posParam);
    THT_clearKeys(scaleParam);
    if (opacityParam) THT_clearKeys(opacityParam);

    if (anim === 'none') {
        // static layout, no keyframes
        posParam.setValue([L.x, L.y], 1);
        scaleParam.setValue(targetScale, 1);
        if (opacityParam) opacityParam.setValue(100, 1);
    } else {
        posParam.setTimeVarying(true);
        scaleParam.setTimeVarying(true);

        var wantSlide = (anim === 'slide' || anim === 'slidefade');
        var wantFade = (anim === 'fade' || anim === 'slidefade');
        var wantPop = (anim === 'pop');

        // Position
        if (wantSlide) {
            THT_addKey2D(posParam, tIn, L.offX, L.offY, THT_INTERP_BEZIER);
            THT_addKey2D(posParam, tIn + d, L.x, L.y, THT_INTERP_BEZIER);
            if (p.animOut) {
                THT_addKey2D(posParam, tOutEnd - d, L.x, L.y, THT_INTERP_BEZIER);
                THT_addKey2D(posParam, tOutEnd, L.offX, L.offY, THT_INTERP_BEZIER);
            }
        } else {
            posParam.setTimeVarying(false);
            posParam.setValue([L.x, L.y], 1);
        }

        // Scale
        if (wantPop) {
            THT_addKey(scaleParam, tIn, 0, THT_INTERP_BEZIER);
            THT_addKey(scaleParam, tIn + d * 0.8, targetScale * 1.08, THT_INTERP_BEZIER);
            THT_addKey(scaleParam, tIn + d, targetScale, THT_INTERP_BEZIER);
            if (p.animOut) {
                THT_addKey(scaleParam, tOutEnd - d, targetScale, THT_INTERP_BEZIER);
                THT_addKey(scaleParam, tOutEnd - d * 0.2, targetScale * 1.08, THT_INTERP_BEZIER);
                THT_addKey(scaleParam, tOutEnd, 0, THT_INTERP_BEZIER);
            }
        } else {
            scaleParam.setTimeVarying(false);
            scaleParam.setValue(targetScale, 1);
        }

        // Opacity
        if (opacityParam) {
            if (wantFade || wantPop) {
                opacityParam.setTimeVarying(true);
                var fadeD = wantPop ? Math.min(d * 0.5, 0.25) : d;
                THT_addKey(opacityParam, tIn, 0, THT_INTERP_LINEAR);
                THT_addKey(opacityParam, tIn + fadeD, 100, THT_INTERP_LINEAR);
                if (p.animOut) {
                    THT_addKey(opacityParam, tOutEnd - fadeD, 100, THT_INTERP_LINEAR);
                    THT_addKey(opacityParam, tOutEnd, 0, THT_INTERP_LINEAR);
                }
            } else {
                opacityParam.setValue(100, 1);
            }
        }
    }

    // ---- drop shadow (optional, best effort) ------------------------------
    var warn = '';
    if (p.dropShadow) {
        var qeErr = THT_applyDropShadow(seq, clip);
        if (qeErr) warn = ' (drop shadow skipped — ' + qeErr + ')';
    }

    var label = { tl: 'top-left', tr: 'top-right', bl: 'bottom-left', br: 'bottom-right', center: 'center' };
    return THT_ok('Overlay applied: ' + (label[p.corner] || p.corner) +
                  ', ' + sizePct + '% size, animation "' + anim + '"' +
                  (p.animOut && anim !== 'none' ? ' in/out' : '') + '.' + warn);
}

/**
 * Remove keyframes and restore the clip to full-frame defaults.
 */
function THT_reset() {
    var found = THT_getSelectedVideoClip();
    if (found.error) return THT_err(found.error);
    var clip = found.clip;

    var motion = THT_findComponent(clip, ['AE.ADBE Motion', 'Motion']);
    var opacityComp = THT_findComponent(clip, ['AE.ADBE Opacity', 'Opacity']);
    var posParam = THT_findParam(motion, ['Position']);
    var scaleParam = THT_findParam(motion, ['Scale']);
    var opacityParam = THT_findParam(opacityComp, ['Opacity']);

    if (posParam) { THT_clearKeys(posParam); posParam.setValue([0.5, 0.5], 1); }
    if (scaleParam) { THT_clearKeys(scaleParam); scaleParam.setValue(100, 1); }
    if (opacityParam) { THT_clearKeys(opacityParam); opacityParam.setValue(100, 1); }

    return THT_ok('Clip reset to full frame (keyframes removed).');
}

/**
 * Lightweight status probe for the panel.
 */
function THT_status() {
    var found = THT_getSelectedVideoClip();
    if (found.error) return THT_err(found.error);
    return THT_ok('Ready: "' + found.clip.name + '" selected.');
}
