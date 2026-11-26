# Bernese BPE Documentation

`~/Bernese_BPE_Documentation` on Sedna builds the website for the configured Bernese GPSUSERs. It combines a generated reference for PCFs, scripts and option files with the manually written Handbook. Use the [[System_Overview/ZDGNSS PCF guide.md|ZDGNSS PCF guide]] to navigate the processing stages and their generated references.

## Project files

- `update_manual.py` reads the `PCF/`, `SCRIPT/` and `OPT/` directories of each configured GPSUSER and generates the manual.
- `update_manual_gui.py` lets you manage GPSUSERs, edit Handbook entries and comments, build the manual and publish it.
- `manual_sources.txt` lists the source GPSUSER directories. `manual_config.json` sets the output directory, source list and optional `handbook_order` for each GPSUSER.
- `manual_additions/handbooks/<gpsuser-slug>/` contains the Markdown pages. For this Handbook the slug is `ck18y530-gpsuser`. The sibling `comments/` and `history/` directories contain manual comments and change records.
- `site/` is the generated output on Sedna. `site/index.html` is the overall GPSUSER overview. With multiple GPSUSERs, each manual is under `site/sources/<gpsuser-slug>/`.
- `publish_manual.sh` commits and pushes the built version. `.github/workflows/deploy-pages.yml` deploys `site/` to GitHub Pages.

## Edit and build

Save Handbook changes under the selected GPSUSER's Handbook folder. Use `handbook_order` in `manual_config.json` to place articles in reading order. Its paths are relative to that GPSUSER's Handbook folder.

Open the GUI from the project directory.

```bash
cd ~/Bernese_BPE_Documentation
python3 update_manual_gui.py
```

- **Only rebuild the manual** rebuilds all configured GPSUSER manuals. Use this after changing the builder or a shared setting.
- **Update GPSUSER** rebuilds the selected GPSUSER and refreshes the common overview. The builder also refreshes any other branches that lack compatible protected downloads for the supplied password.
- **Only publish to GitHub** uses the existing `site/` output. Choose it after checking the local build.

For a local review, clear **Push site/ to GitHub after a successful build** before starting the build.

## Preview and check downloads

Run a local web server from the project directory and open `http://localhost:8000/`. If the browser is on another computer, use an SSH tunnel to the server on Sedna.

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
```

The build takes the shared download password from the GUI or from `DOCBUILDER_DOWNLOAD_PASSWORD`. For each GPSUSER, test a representative download with an incorrect password and then with the intended password. The HTML documentation and Handbook text are visible to anyone who can access the Pages site. The password protects the downloaded source files.

## Publish a reviewed build

Check `git status --short` from the project directory before using **Only publish to GitHub**. The publish script uses `git add -A`, so it includes pending changes across the checkout.

The script checks for `site/index.html`, rejects old `source_files` directories and requires the `downloads/.protected` marker for each generated manual. It then pushes the commit to `origin/main`. In GitHub, check that **Deploy manual site** succeeded for that commit and open the deployed site to confirm the changes.
