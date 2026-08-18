/*
 * Minimal CSInterface shim.
 *
 * Adobe ships a full CSInterface.js with the CEP SDK; this covers only the
 * surface this panel actually uses, so the extension stays self-contained
 * with no vendored dependency to keep in sync.
 *
 * Everything here is a thin wrapper over window.__adobe_cep__, which the CEP
 * runtime injects into the panel's JS context.
 */

function CSInterface() {}

CSInterface.prototype.hostEnvironment = function () {
  try {
    return JSON.parse(window.__adobe_cep__.getHostEnvironment());
  } catch (e) {
    return null;
  }
};

CSInterface.prototype.getOSInformation = function () {
  try {
    return window.__adobe_cep__.getSystemPath ? navigator.platform : 'unknown';
  } catch (e) {
    return 'unknown';
  }
};

CSInterface.prototype.isWindows = function () {
  return /win/i.test(navigator.platform);
};

/**
 * Run an ExtendScript expression in the host app.
 * The callback receives the function's return value as a string.
 */
CSInterface.prototype.evalScript = function (script, callback) {
  if (typeof callback !== 'function') {
    callback = function () {};
  }
  window.__adobe_cep__.evalScript(script, callback);
};

/**
 * pathType is one of the SystemPath constants below. The runtime returns a
 * file:// URL, which is not what any filesystem call wants, so strip it.
 */
CSInterface.prototype.getSystemPath = function (pathType) {
  var path = decodeURI(window.__adobe_cep__.getSystemPath(pathType));
  if (this.isWindows()) {
    return path.replace('file:///', '');
  }
  return path.replace('file://', '');
};

CSInterface.prototype.addEventListener = function (type, listener, obj) {
  window.__adobe_cep__.addEventListener(type, listener, obj);
};

CSInterface.prototype.getHostCapabilities = function () {
  try {
    return JSON.parse(window.__adobe_cep__.getHostCapabilities());
  } catch (e) {
    return null;
  }
};

var SystemPath = {
  USER_DATA: 'userData',
  COMMON_FILES: 'commonFiles',
  MY_DOCUMENTS: 'myDocuments',
  APPLICATION: 'application',
  EXTENSION: 'extension',
  HOST_APPLICATION: 'hostApplication'
};
