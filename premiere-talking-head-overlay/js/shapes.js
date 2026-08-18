/*
 * Shape rendering.
 *
 * Two PNGs come out of here, drawn on identically sized canvases so they line
 * up perfectly when the host script gives them the same Position:
 *
 *   matte  - solid white shape on transparent. Feeds Track Matte Key.
 *   border - the stroke only, in the user's colour, transparent inside, so the
 *            talking head shows through.
 *
 * Canvas size is the shape plus the full stroke plus a small bleed, and the
 * shape is centred in it. That keeps the graphic's anchor point at the shape's
 * own centre, so scaling it animates about the shape rather than about the
 * middle of the frame.
 */

var Shapes = (function () {
  var BLEED = 8; // px of transparent margin; keeps soft edges from clipping

  function canvasSize(opts) {
    return {
      w: Math.ceil(opts.width + opts.borderWidth + BLEED * 2),
      h: Math.ceil(opts.height + opts.borderWidth + BLEED * 2)
    };
  }

  function roundRectPath(ctx, x, y, w, h, r) {
    // A radius past half the short side stops making sense; clamp to a capsule.
    r = Math.max(0, Math.min(r, Math.min(w, h) / 2));
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.arcTo(x + w, y, x + w, y + r, r);
    ctx.lineTo(x + w, y + h - r);
    ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
    ctx.lineTo(x + r, y + h);
    ctx.arcTo(x, y + h, x, y + h - r, r);
    ctx.lineTo(x, y + r);
    ctx.arcTo(x, y, x + r, y, r);
    ctx.closePath();
  }

  /** Trace the shape centred on a canvas of the given size. */
  function shapePath(ctx, opts, size) {
    var x = (size.w - opts.width) / 2;
    var y = (size.h - opts.height) / 2;
    roundRectPath(ctx, x, y, opts.width, opts.height, opts.radius);
  }

  function newCanvas(size) {
    var c = document.createElement('canvas');
    c.width = size.w;
    c.height = size.h;
    return c;
  }

  /** White-on-transparent silhouette. Track Matte Key reads its alpha. */
  function renderMatte(opts) {
    var size = canvasSize(opts);
    var c = newCanvas(size);
    var ctx = c.getContext('2d');
    shapePath(ctx, opts, size);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    return c;
  }

  /**
   * Stroke only. Drawn centred on the path, so half the width sits inside the
   * matte and half outside - the same way a border reads in Premiere's own
   * shape tools.
   */
  function renderBorder(opts) {
    var size = canvasSize(opts);
    var c = newCanvas(size);
    var ctx = c.getContext('2d');
    if (opts.borderWidth <= 0) {
      return c; // fully transparent; the host still places it, so toggling
                // the border later never has to restructure the track stack
    }

    if (opts.shadow > 0) {
      ctx.save();
      ctx.shadowColor = 'rgba(0,0,0,0.55)';
      ctx.shadowBlur = opts.shadow;
      ctx.shadowOffsetY = Math.round(opts.shadow / 3);
      shapePath(ctx, opts, size);
      ctx.lineWidth = opts.borderWidth;
      ctx.strokeStyle = opts.borderColor;
      ctx.stroke();
      ctx.restore();
    }

    shapePath(ctx, opts, size);
    ctx.lineWidth = opts.borderWidth;
    ctx.strokeStyle = opts.borderColor;
    ctx.lineJoin = 'round';
    ctx.stroke();
    return c;
  }

  /** Panel preview: the whole frame, scaled down, with the shape in place. */
  function renderPreview(canvas, opts, seq, scale) {
    var ctx = canvas.getContext('2d');
    canvas.width = Math.round(seq.width * scale);
    canvas.height = Math.round(seq.height * scale);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Stand-in for whatever is on the background track.
    var g = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    g.addColorStop(0, '#2b3350');
    g.addColorStop(1, '#171a27');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    var cx = opts.centerX * canvas.width;
    var cy = opts.centerY * canvas.height;
    var w = opts.width * scale;
    var h = opts.height * scale;

    ctx.save();
    ctx.translate(cx, cy);

    // Clip to the shape and fill with a stand-in for the talking head.
    ctx.save();
    roundRectPath(ctx, -w / 2, -h / 2, w, h, opts.radius * scale);
    ctx.clip();
    var hg = ctx.createLinearGradient(0, -h / 2, 0, h / 2);
    hg.addColorStop(0, '#6b7a99');
    hg.addColorStop(1, '#3d475e');
    ctx.fillStyle = hg;
    ctx.fillRect(-w / 2, -h / 2, w, h);
    ctx.fillStyle = 'rgba(255,255,255,0.30)';
    ctx.font = Math.max(9, Math.round(h / 9)) + 'px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('talking head', 0, 0);
    ctx.restore();

    if (opts.borderWidth > 0) {
      roundRectPath(ctx, -w / 2, -h / 2, w, h, opts.radius * scale);
      ctx.lineWidth = Math.max(1, opts.borderWidth * scale);
      ctx.strokeStyle = opts.borderColor;
      ctx.lineJoin = 'round';
      ctx.stroke();
    }
    ctx.restore();
  }

  /** Strip the data-URL prefix; cep.fs wants raw base64. */
  function toBase64(canvas) {
    return canvas.toDataURL('image/png').replace(/^data:image\/png;base64,/, '');
  }

  return {
    canvasSize: canvasSize,
    renderMatte: renderMatte,
    renderBorder: renderBorder,
    renderPreview: renderPreview,
    toBase64: toBase64
  };
})();
