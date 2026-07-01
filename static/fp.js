/* Lightweight device fingerprint for signup anti-abuse (self-hosted to satisfy
   CSP script-src 'self'). Not a hardware ID — it's one best-effort signal that
   raises the cost of mass fake signups; combined server-side with email verify
   and velocity limits. Returns a hex string, or null if it can't compute one. */
(function () {
  async function sha256hex(str) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
  }

  function canvasFp() {
    try {
      const c = document.createElement("canvas");
      const ctx = c.getContext("2d");
      ctx.textBaseline = "top";
      ctx.font = "14px 'Arial'";
      ctx.fillStyle = "#f60"; ctx.fillRect(125, 1, 62, 20);
      ctx.fillStyle = "#069"; ctx.fillText("Tokverse❤", 2, 15);
      ctx.fillStyle = "rgba(102,204,0,0.7)"; ctx.fillText("Tokverse❤", 4, 17);
      return c.toDataURL();
    } catch (e) { return "no-canvas"; }
  }

  function webglFp() {
    try {
      const gl = document.createElement("canvas").getContext("webgl");
      const dbg = gl.getExtension("WEBGL_debug_renderer_info");
      const v = gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) || "";
      const r = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) || "";
      return v + "~" + r;
    } catch (e) { return "no-webgl"; }
  }

  window.getFingerprint = async function () {
    try {
      const n = navigator, s = screen;
      const parts = [
        n.userAgent, n.language, (n.languages || []).join(","), n.platform || "",
        n.hardwareConcurrency || "", n.deviceMemory || "",
        s.width + "x" + s.height + "x" + s.colorDepth,
        (Intl.DateTimeFormat().resolvedOptions().timeZone) || "",
        new Date().getTimezoneOffset(), n.maxTouchPoints || 0,
        canvasFp(), webglFp(),
      ];
      return await sha256hex(parts.join("|"));
    } catch (e) { return null; }
  };
})();
