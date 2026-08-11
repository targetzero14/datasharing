/**
 * Minimal CSInterface shim for CEP.
 *
 * This implements only what this panel needs (evalScript). If you prefer the
 * full official library, drop in Adobe's CSInterface.js from
 * https://github.com/Adobe-CEP/CEP-Resources — it is a drop-in replacement.
 */
function CSInterface() {}

CSInterface.prototype.evalScript = function (script, callback) {
  if (typeof window.__adobe_cep__ === 'undefined') {
    if (callback) {
      callback('{"ok":false,"message":"Not running inside a CEP host (open this panel from Premiere Pro: Window > Extensions)."}');
    }
    return;
  }
  window.__adobe_cep__.evalScript(script, callback || function () {});
};
