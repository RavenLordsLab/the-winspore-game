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

  window.setupGamepad = setupGamepad;
  window.gamepadRumble = gamepadRumble;
})();
