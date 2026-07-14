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

> Mobile: on phones/tablets an on-screen touch pad appears automatically. It's
> built from each game's own key mapping by `gamepad.js`, so the same buttons that
> work with a controller work by touch. Add `?touch=1` to a game's URL to preview
> the pad on a desktop, or `?touch=0` to hide it.

## Enable GitHub Pages

1. Push this repo to GitHub.
2. Repo **Settings → Pages**.
3. Under **Build and deployment**, set **Source: Deploy from a branch**.
4. Select branch `main`, folder `/ (root)`, and **Save**.
5. Wait ~1 minute, then open the URL shown at the top of the Pages settings.
