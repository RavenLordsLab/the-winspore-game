// Shared gamepad helper: polls connected gamepads and dispatches synthetic
// KeyboardEvents so games that already listen for keys "just work" with a
// wireless controller. Supports up to 2 players (gamepad index 0 -> P1, 1 -> P2).
//
// Usage:
//   setupGamepad({
//     players: [
//       { up:'ArrowUp', down:'ArrowDown', left:'ArrowLeft', right:'ArrowRight',
//         a:'Space', b:'Enter', x:'KeyF', y:'KeyG', start:'Enter', back:'Escape' },
//       // optional second player...
//     ],
//     // if true, gamepad 1 also drives player-1 mapping (handy for solo games)
//     mirrorSingle: false
//   });
//
// Each binding can be a string like 'KeyA', 'ArrowUp', 'Space', 'Enter',
// 'Period', 'Slash', etc. (We translate that to a sensible (key, code) pair.)

(function () {
  const STICK_DEADZONE = 0.35;

  // Map a "code-ish" string to a {key, code} pair that satisfies both common
  // game patterns: `e.key` (e.g. 'a', ' ', 'ArrowUp') and `e.code` ('KeyA', 'Space').
  function toKeyPair(token) {
    if (!token) return null;
    if (typeof token !== 'string') return null;
    // Direct overrides
    const m = {
      Space:        { key: ' ',         code: 'Space' },
      Enter:        { key: 'Enter',     code: 'Enter' },
      Escape:       { key: 'Escape',    code: 'Escape' },
      ArrowUp:      { key: 'ArrowUp',   code: 'ArrowUp' },
      ArrowDown:    { key: 'ArrowDown', code: 'ArrowDown' },
      ArrowLeft:    { key: 'ArrowLeft', code: 'ArrowLeft' },
      ArrowRight:   { key: 'ArrowRight',code: 'ArrowRight' },
      Period:       { key: '.',         code: 'Period' },
      Slash:        { key: '/',         code: 'Slash' },
      Semicolon:    { key: ';',         code: 'Semicolon' },
      Quote:        { key: "'",         code: 'Quote' },
      Comma:        { key: ',',         code: 'Comma' },
    };
    if (m[token]) return m[token];
    // KeyA..KeyZ -> {key:'a', code:'KeyA'}
    if (/^Key[A-Z]$/.test(token)) {
      const letter = token.slice(3).toLowerCase();
      return { key: letter, code: token };
    }
    // Digit0..Digit9
    if (/^Digit[0-9]$/.test(token)) {
      const d = token.slice(5);
      return { key: d, code: token };
    }
    // Fallback: use as both
    return { key: token, code: token };
  }

  function dispatchKey(type, pair) {
    if (!pair) return;
    const ev = new KeyboardEvent(type, {
      key: pair.key,
      code: pair.code,
      bubbles: true,
      cancelable: true,
    });
    // Some games index by lowercase e.key. KeyboardEvent.key is already
    // lowercase for letter keys here, so this is fine.
    window.dispatchEvent(ev);
    document.dispatchEvent(ev);
  }

  // Build the canonical button list for one player. Maps controller inputs
  // (D-pad index, stick direction, face buttons) to one of the named slots.
  const BUTTON_SLOTS = [
    { slot: 'a',     idx: 0  },  // south face
    { slot: 'b',     idx: 1  },  // east face
    { slot: 'x',     idx: 2  },  // west face
    { slot: 'y',     idx: 3  },  // north face
    { slot: 'lb',    idx: 4  },
    { slot: 'rb',    idx: 5  },
    { slot: 'lt',    idx: 6  },
    { slot: 'rt',    idx: 7  },
    { slot: 'back',  idx: 8  },
    { slot: 'start', idx: 9  },
    { slot: 'up',    idx: 12 },  // d-pad
    { slot: 'down',  idx: 13 },
    { slot: 'left',  idx: 14 },
    { slot: 'right', idx: 15 },
  ];

  function readPlayer(gp, mapping, prevState) {
    // Build current logical state per slot.
    const state = {};
    for (const { slot, idx } of BUTTON_SLOTS) {
      const btn = gp.buttons[idx];
      state[slot] = !!(btn && btn.pressed);
    }
    // Left stick augments d-pad direction slots.
    const ax = gp.axes[0] || 0, ay = gp.axes[1] || 0;
    if (ax < -STICK_DEADZONE) state.left  = true;
    if (ax >  STICK_DEADZONE) state.right = true;
    if (ay < -STICK_DEADZONE) state.up    = true;
    if (ay >  STICK_DEADZONE) state.down  = true;

    // Diff against prev and dispatch.
    for (const slot of Object.keys(state)) {
      const now = state[slot], was = !!prevState[slot];
      if (now === was) continue;
      const token = mapping[slot];
      if (!token) continue;
      const pair = toKeyPair(token);
      dispatchKey(now ? 'keydown' : 'keyup', pair);
    }
    return state;
  }

  function setupGamepad(config) {
    const players = (config && config.players) || [];
    const mirrorSingle = !!(config && config.mirrorSingle);
    const prev = [{}, {}, {}, {}];

    window.addEventListener('gamepadconnected', e => {
      console.log('[gamepad] connected:', e.gamepad.id, 'index', e.gamepad.index);
    });
    window.addEventListener('gamepaddisconnected', e => {
      console.log('[gamepad] disconnected:', e.gamepad.id, 'index', e.gamepad.index);
    });

    function loop() {
      const pads = navigator.getGamepads ? navigator.getGamepads() : [];
      for (let i = 0; i < pads.length; i++) {
        const gp = pads[i];
        if (!gp) continue;
        let mapping;
        if (mirrorSingle) {
          mapping = players[0];
        } else {
          mapping = players[i];
        }
        if (!mapping) continue;
        prev[i] = readPlayer(gp, mapping, prev[i] || {});
      }
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  }

  function gamepadRumble(playerIdx, strong, weak, durationMs) {
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    const gp = pads[playerIdx];
    if (!gp) return;
    const act = gp.vibrationActuator;
    if (!act || !act.playEffect) return;
    try {
      act.playEffect('dual-rumble', {
        startDelay: 0,
        duration: Math.max(20, durationMs|0),
        weakMagnitude: Math.max(0, Math.min(1, weak)),
        strongMagnitude: Math.max(0, Math.min(1, strong)),
      });
    } catch (e) {}
  }

  // ---------------------------------------------------------------------------
  // On-screen TOUCH CONTROLS for phones/tablets.
  //
  // Reuses the exact same dispatchKey/toKeyPair path as the gamepad poller, so
  // any game that already "works with a controller" also works with the on-screen
  // pad — no per-game changes needed. Driven by the same player mapping that a
  // game passes to setupGamepad().
  // ---------------------------------------------------------------------------

  const IS_TOUCH = (typeof window !== 'undefined') &&
    (('ontouchstart' in window) || (navigator.maxTouchPoints > 0));
  // ?touch=1 forces the pad on (handy for testing on a desktop); ?touch=0 hides it.
  function touchForced() {
    try {
      const q = new URLSearchParams(location.search).get('touch');
      if (q === '1') return true;
      if (q === '0') return 'off';
    } catch (e) {}
    return null;
  }

  function onReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn, { once: true });
    } else {
      fn();
    }
  }

  // Add a viewport meta + light responsive CSS so fixed-size canvases fit a phone
  // screen and the page doesn't double-tap-zoom or scroll under the controls.
  let chromeInjected = false;
  function injectMobileChrome() {
    if (chromeInjected) return;
    chromeInjected = true;
    if (!document.querySelector('meta[name="viewport"]')) {
      const m = document.createElement('meta');
      m.name = 'viewport';
      m.content = 'width=device-width, initial-scale=1.0, viewport-fit=cover';
      (document.head || document.documentElement).appendChild(m);
    }
    const style = document.createElement('style');
    style.setAttribute('data-gp-mobile', '');
    style.textContent = `
      html, body { max-width: 100%; overflow-x: hidden; touch-action: manipulation; }
      canvas { max-width: 100%; height: auto; }
      /* On-screen controller */
      #gp-touch { position: fixed; inset: 0; z-index: 2147483000; pointer-events: none;
        -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }
      #gp-touch .gp-cluster { position: absolute; bottom: max(16px, env(safe-area-inset-bottom));
        display: grid; pointer-events: none; }
      #gp-touch .gp-dpad { left: max(12px, env(safe-area-inset-left));
        grid-template-columns: repeat(3, 58px); grid-template-rows: repeat(3, 58px); gap: 4px; }
      #gp-touch .gp-actions { right: max(12px, env(safe-area-inset-right));
        grid-auto-flow: row dense; grid-template-columns: repeat(2, 68px); gap: 10px; align-items: end; }
      #gp-touch .gp-btn { pointer-events: auto; display: flex; align-items: center; justify-content: center;
        font: 600 18px/1 system-ui, sans-serif; color: #fff; background: rgba(30,34,54,0.55);
        border: 1.5px solid rgba(255,255,255,0.35); border-radius: 14px; backdrop-filter: blur(2px);
        touch-action: none; -webkit-tap-highlight-color: transparent; }
      #gp-touch .gp-btn:active { background: rgba(108,140,255,0.75); transform: scale(0.94); }
      #gp-touch .gp-dpad .gp-btn { width: 58px; height: 58px; border-radius: 12px; font-size: 22px; }
      #gp-touch .gp-actions .gp-btn { width: 68px; height: 68px; border-radius: 50%; font-size: 20px; }
      #gp-touch .gp-slot-empty { visibility: hidden; }
      #gp-touch .gp-start { position: absolute; top: max(10px, env(safe-area-inset-top));
        right: max(10px, env(safe-area-inset-right)); width: auto; height: 40px; padding: 0 16px;
        border-radius: 20px; font-size: 15px; }
      @media (min-height: 560px) and (orientation: portrait) {
        #gp-touch .gp-dpad { grid-template-columns: repeat(3, 64px); grid-template-rows: repeat(3, 64px); }
        #gp-touch .gp-dpad .gp-btn { width: 64px; height: 64px; }
      }
    `;
    (document.head || document.documentElement).appendChild(style);
  }

  const DIR_GLYPH = { up: '▲', down: '▼', left: '◀', right: '▶' };
  // Grid positions in the 3x3 dpad (row/col, 1-indexed).
  const DPAD_POS = {
    up:    'grid-row:1;grid-column:2',
    left:  'grid-row:2;grid-column:1',
    right: 'grid-row:2;grid-column:3',
    down:  'grid-row:3;grid-column:2',
  };

  let touchBuilt = false;

  // Make an element fire keydown on press and keyup on release for a given token.
  function bindButton(el, token) {
    const pair = toKeyPair(token);
    if (!pair) return;
    let down = false;
    const press = (e) => {
      if (e) { e.preventDefault(); e.stopPropagation(); }
      if (down) return;
      down = true;
      dispatchKey('keydown', pair);
    };
    const release = (e) => {
      if (e) { e.preventDefault(); e.stopPropagation(); }
      if (!down) return;
      down = false;
      dispatchKey('keyup', pair);
    };
    el.addEventListener('pointerdown', press);
    el.addEventListener('pointerup', release);
    el.addEventListener('pointercancel', release);
    el.addEventListener('pointerleave', release);
    // Safety: release if the pointer is lifted anywhere.
    window.addEventListener('pointerup', release);
    // Prevent the browser turning a long-press into a context menu / selection.
    el.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  function makeBtn(label, cls, styleText) {
    const b = document.createElement('div');
    b.className = 'gp-btn' + (cls ? ' ' + cls : '');
    b.textContent = label;
    if (styleText) b.style.cssText = styleText;
    return b;
  }

  // Build the on-screen pad from a player mapping (same shape passed to setupGamepad).
  function setupTouchControls(mapping, opts) {
    opts = opts || {};
    const forced = touchForced();
    if (forced === 'off') return;
    if (!IS_TOUCH && forced !== true) return;   // desktop: skip unless ?touch=1
    if (touchBuilt) return;                      // one pad per page
    if (!mapping) return;
    touchBuilt = true;

    onReady(() => {
      injectMobileChrome();

      const root = document.createElement('div');
      root.id = 'gp-touch';

      // --- D-pad (only the directions this game actually uses) ---
      const dirs = ['up', 'down', 'left', 'right'].filter(d => mapping[d]);
      if (dirs.length) {
        const dpad = document.createElement('div');
        dpad.className = 'gp-cluster gp-dpad';
        for (const d of dirs) {
          const b = makeBtn(DIR_GLYPH[d], null, DPAD_POS[d]);
          bindButton(b, mapping[d]);
          dpad.appendChild(b);
        }
        root.appendChild(dpad);
      }

      // --- Action buttons: unique keys among a/b/x/y (dedup shared bindings) ---
      const actionOrder = ['a', 'b', 'x', 'y', 'lb', 'rb'];
      const seen = new Set();
      const actions = [];
      for (const slot of actionOrder) {
        const tok = mapping[slot];
        if (!tok || seen.has(tok)) continue;
        seen.add(tok);
        actions.push({ slot, tok });
        if (actions.length >= 4) break;
      }
      if (actions.length) {
        const pad = document.createElement('div');
        pad.className = 'gp-cluster gp-actions';
        for (const { slot, tok } of actions) {
          const b = makeBtn(slot.toUpperCase(), null, null);
          bindButton(b, tok);
          pad.appendChild(b);
        }
        root.appendChild(pad);
      }

      // --- Start / pause button (top-right) ---
      const startTok = mapping.start || mapping.back;
      if (startTok) {
        const s = makeBtn('❚❚', 'gp-start', null);
        bindButton(s, startTok);
        root.appendChild(s);
      }

      document.body.appendChild(root);
    });
  }

  // Wrap setupGamepad so any game that configures a controller also gets the
  // on-screen pad automatically, built from player 1's mapping.
  const _setupGamepad = setupGamepad;
  function setupGamepadWithTouch(config) {
    _setupGamepad(config);
    const players = (config && config.players) || [];
    if (players[0]) setupTouchControls(players[0], { config });
  }

  window.setupGamepad = setupGamepadWithTouch;
  window.setupTouchControls = setupTouchControls;
  window.gamepadRumble = gamepadRumble;
})();
