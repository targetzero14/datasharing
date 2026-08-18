# Talking Head Overlay

A Premiere Pro panel that builds a shaped, bordered talking-head overlay on your
timeline — pick the shape, size, position, border colour and pop animation in the
panel, hit Apply, and it assembles the whole thing on the selected clip.

Version 0.1.0 — first working slice: rounded rectangle (circle and squircle are
just radius presets of it), coloured border, optional shadow, scale-pop in and out.

## What it actually does

Premiere's scripting API can't draw masks, so the panel generates the artwork
itself and assembles a track stack:

```
V(n+2)   border graphic     stroke in your colour, transparent inside
V(n+1)   matte graphic      white silhouette, read by Track Matte Key
V(n)     talking head       Track Matte Key pointed at V(n+1)
V(n-1)   your background    whatever was already there
```

The two PNGs are rendered on identically sized canvases with the shape centred,
so they share one Position value and their anchor points sit at the shape's own
centre — that's what makes the pop scale about the shape instead of flying in
from the middle of the frame.

Generated PNGs land in a `Talking Head Overlay` folder next to your project file
(or in the CEP user-data folder if the project is unsaved), and get imported into
a bin of the same name. Re-applying the same look reuses the same PNG rather than
piling up duplicates.

## Install

Requires Premiere Pro 14.0 (2020) or newer. Built and tested against the 25.x /
26.x API surface.

**macOS**

```bash
git clone <this repo>
cd premiere-talking-head-overlay
./install.sh
```

**Windows**

```powershell
git clone <this repo>
cd premiere-talking-head-overlay
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Both scripts turn on `PlayerDebugMode` (required for unsigned extensions) and
copy the panel into your per-user CEP extensions folder. Restart Premiere, then
open **Window → Extensions → Talking Head Overlay**.

## Use

1. Put your background on a track, your talking head on the track above it.
2. Select the talking-head clip in the timeline.
3. Hit **Refresh** in the panel — it should name the clip and its track.
4. Dial in shape, position, border and animation. The preview updates live.
5. **Apply to selected clip.**

The status pane at the bottom logs every step the host script took. If something
goes wrong, that log says which step and which parameter name — paste it back and
it's usually a one-line fix.

## Known rough edges

These are the places most likely to need a tweak on your specific build. All of
them surface in the status log rather than failing silently.

- **Keyframe time base.** Premiere is inconsistent across versions about whether
  keyframe times on a timeline clip are measured from the sequence start or the
  clip start. If the pop lands in the wrong place, open **Advanced** and tick
  *Keyframe times are clip-relative*, then re-apply.
- **Effect name is English-only.** The Track Matte Key lookup goes by display
  name. A non-English Premiere UI needs the localised string.
- **`Matte` dropdown indexing** is assumed to be `0 = None, 1 = Video 1, …`. The
  log prints the value it set, so it's easy to verify.
- **Track creation uses the QE DOM**, which is undocumented and occasionally
  moves between versions. If it fails, the error tells you how many video tracks
  to add by hand.
- **Adding tracks shifts track indices.** Apply to one clip at a time for now;
  batching across a whole track is a follow-up.

## Debugging

With the panel open, browse to <http://localhost:8088> for CEF devtools on the
panel UI. The port is set in `.debug`.

Host-script errors come back through the panel's status pane rather than a
Premiere dialog, so there's no need to watch the ExtendScript console.

## Layout

```
CSXS/manifest.xml    extension registration, host version range, CEF flags
index.html           panel markup
css/style.css        panel styling
js/CSInterface.js    minimal shim over window.__adobe_cep__
js/shapes.js         canvas rendering: matte, border, live preview
js/main.js           panel logic, file writing, host calls
jsx/host.jsx         ExtendScript: import, place, matte key, keyframes
```

## Next

- More shapes: hexagon, custom SVG import
- More in/out styles: slide, iris, wipe, fade
- Saveable named presets
- Apply across every clip on a track in one pass
