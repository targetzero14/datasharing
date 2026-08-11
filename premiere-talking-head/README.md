# Talking Head Toolkit — Premiere Pro panel

A lightweight Premiere Pro extension (CEP panel) for creating talking-head
picture-in-picture overlays with one click, plus simple intro/outro
animations — no manual keyframing.

## What it does

Select your camera clip on an upper video track (with your screen recording,
slides, or gameplay underneath), open the panel, and click **Apply Overlay**:

- **Position presets** — any corner of the frame, or centered, with an
  adjustable edge margin.
- **Size presets** — Small (25%), Medium (33%), Large (45%) of frame width.
- **Animations** — slide in, pop in, fade in, or slide + fade, with an
  adjustable duration (0.2–1.5s) and an optional mirrored animate-out at the
  end of the clip.
- **Drop shadow** — optionally adds Premiere's Drop Shadow effect to lift the
  overlay off the background.
- **Reset Clip** — removes the keyframes and restores the clip to full frame.

Everything is done with ordinary Motion/Opacity keyframes on the clip, so you
can fine-tune the result in the Effect Controls panel afterwards.

## Requirements

- Adobe Premiere Pro CC 2019 (13.0) or newer, including current 2024/2025
  releases (CEP extensions are still supported alongside UXP).
- The panel is unsigned, so CEP "PlayerDebugMode" must be enabled — the
  install scripts below do this for you.

## Install

### macOS

```bash
cd premiere-talking-head/install
bash install-mac.sh
```

### Windows

Double-click `premiere-talking-head\install\install-windows.bat` (or run it
from a terminal).

Then restart Premiere Pro and open **Window > Extensions > Talking Head
Toolkit**.

### Manual install

1. Copy the `premiere-talking-head` folder (everything except `install/`) to:
   - macOS: `~/Library/Application Support/Adobe/CEP/extensions/com.talkingheadtoolkit.panel`
   - Windows: `%APPDATA%\Adobe\CEP\extensions\com.talkingheadtoolkit.panel`
2. Enable debug extensions:
   - macOS: `defaults write com.adobe.CSXS.11 PlayerDebugMode 1`
   - Windows: add a String value `PlayerDebugMode = 1` under
     `HKEY_CURRENT_USER\Software\Adobe\CSXS.11`
   (Repeat for `CSXS.9`, `CSXS.10`, and `CSXS.12` to cover other Premiere
   versions.)
3. Restart Premiere Pro.

## Usage

1. Put your talking-head clip on a video track **above** your main content.
2. Select the clip in the timeline.
3. In the panel, choose a corner, size, margin, and animation.
4. Click **Apply Overlay**.

Tips:

- "Also animate out" mirrors the intro animation at the clip's end — trim the
  clip to its final length before applying, or re-apply after trimming.
- Re-applying replaces the previous keyframes, so it's safe to iterate.
- Use **Reset Clip** to go back to a full-frame, keyframe-free clip.

## Notes & limitations

- Size presets are computed against the sequence frame; if Premiere doesn't
  report the source resolution, the panel assumes the camera source matches
  the sequence resolution, so a 4K source in a 1080p timeline may need a
  size tweak (just drag the Scale value in Effect Controls).
- Circular masks aren't scriptable through Premiere's API, so this panel
  doesn't do round overlays. For a round look, apply an ellipse mask to the
  clip's Opacity manually after applying the layout.
- The drop shadow is applied through Premiere's QE DOM, which is
  undocumented; if it can't locate the clip, the panel applies everything
  else and tells you the shadow was skipped.

## Development

- The panel UI lives in `index.html` / `js/main.js`; Premiere-side automation
  is in `jsx/host.jsx` (ExtendScript).
- `.debug` maps the panel to a Chrome DevTools remote-debug port
  (http://localhost:8092) when PlayerDebugMode is on.
- `js/CSInterface.js` is a minimal shim; Adobe's full
  [CSInterface.js](https://github.com/Adobe-CEP/CEP-Resources) is a drop-in
  replacement if you extend the panel.
- To distribute without PlayerDebugMode, package and sign with
  [ZXPSignCmd](https://github.com/Adobe-CEP/CEP-Resources/tree/master/ZXPSignCMD):
  `ZXPSignCmd -sign premiere-talking-head talking-head.zxp cert.p12 <password>`
