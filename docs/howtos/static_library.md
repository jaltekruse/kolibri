# Exporting the library for a static web host

The `static_library` plugin writes a Kolibri's channels as plain files that any static web host can serve: GitHub Pages, a bucket behind a CDN, or `python -m http.server`. Visitors browse, search and use the channels as a guest does in Learn, with nothing running on the server.

## How it works

The page is Learn's own library, topic and resource pages, in the plugin's `app` bundle. A Kolibri page asks Kolibri's API for everything it shows; this one has no Kolibri to ask, so the plugin gives the HTTP client an adapter (`setRequestAdapter` in `kolibri/utils/baseClient`) that answers each request from JSON files written beside the page:

- `channels.json` and `nodes/<id>.json` hold exactly what `channel/?available=true` and `contentnode/<id>/` return.
- `children/<id>.json` holds a topic's children, serialized the same way. The adapter builds `contentnode_tree/<id>/` answers from them, paging children as Kolibri does.
- `index/<channel id>.json` holds the fields of each node that `contentnode/` filters on. The adapter filters, searches (every word, in titles and descriptions, as Kolibri does) and pages over them, and works out the labels of what it found.
- `library.json` holds each channel's root, the labels of the whole library and its first page of nodes, so the library page loads without any channel's index.

Starting and updating a session with a resource (`trackprogress/`) is kept in the page, as Kolibri keeps no progress for guests beyond the session. So exercises can be practised and completed, but nothing is saved.

Content files are copied (hard linked where possible), and HTML5 apps, H5P and other archives are unzipped as Kolibri's zip content server would serve them.

## Exporting

The page loads the built frontend, so first build it for production:

```sh
pnpm run build
```

Then export, with production settings (not `kolibri.deployment.default.settings.dev`):

```sh
kolibri manage exportstaticlibrary ./site
kolibri manage exportstaticlibrary ./site --channel <channel id> --channel <channel id>
```

Every file goes where its URL on this Kolibri points, under the output folder. Serve the folder as the site's root, and open the page at `URL_PATH_PREFIX`:

```sh
cd site && python -m http.server 8080
# then open http://localhost:8080/ (or http://localhost:8080/<URL_PATH_PREFIX>)
```

To host it under a path, such as `https://example.github.io/library/`, export with that path as the prefix: `KOLIBRI_URL_PATH_PREFIX=/library/ KOLIBRI_ZIP_CONTENT_URL_PATH_PREFIX=/library/ kolibri manage exportstaticlibrary ./site`, and publish `site/library/`.

## Videos from YouTube

With Kolibri's `YOUTUBE_PLAYBACK` option on, the media player plays a video with a YouTube id from YouTube, and the page does too: it frames the YouTube player page the export copies to `content/static/youtube/`. To leave such videos' files out of the export, add `--stream`:

```sh
KOLIBRI_YOUTUBE_PLAYBACK=true kolibri manage exportstaticlibrary ./site --stream
```

Their files are written into the JSON as Kolibri returns a file that isn't on the device, so where YouTube can't play a video, the page says the video isn't on the device. Thumbnails and subtitles are still exported. Videos imported to play from YouTube (`importcontent --stream`, or "Play videos from YouTube instead of downloading them" on the import page) have no files to export in the first place.

## Limitations

- The page is in English: it reuses Learn's pages, whose translations are loaded for Learn's own bundle.
- Archives are served from the page's own origin, as a static host has only the one. Kolibri serves them from a separate origin so that an HTML5 app can't reach the page that frames it; with no accounts or server behind a static library, there is little for an app to reach.
- Only what a guest does in Learn is answered: there are no accounts, classes, bookmarks or downloads.
- Search reads each channel's whole index into the browser, which for a channel the size of Khan Academy's is several megabytes.
