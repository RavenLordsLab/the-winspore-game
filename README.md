# 🎮 Game Arcade

A collection of self-contained HTML browser games. Open `index.html` for the game menu, or play the live version once GitHub Pages is enabled (see below).

## Play online

Once published, the arcade is available at:

```
https://<your-username>.github.io/<repo-name>/
```

Share that link — it works on any mobile phone browser.

## Games

All games are single-file HTML. Some use the shared `gamepad.js` for NC300 wireless
gamepad support; a few 3D games load `three.js` from a CDN.

> Note: several games were built for keyboard/gamepad and don't yet have touch
> controls, so they load on phones but play best with a physical controller.

## Enable GitHub Pages

1. Push this repo to GitHub.
2. Repo **Settings → Pages**.
3. Under **Build and deployment**, set **Source: Deploy from a branch**.
4. Select branch `main`, folder `/ (root)`, and **Save**.
5. Wait ~1 minute, then open the URL shown at the top of the Pages settings.
