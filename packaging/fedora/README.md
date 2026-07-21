# Fedora packaging for BambuStudio

Unofficial Fedora RPM packaging of [BambuStudio](https://github.com/bambulab/BambuStudio).
Upstream ships no Fedora build — only an Ubuntu AppImage, plus Windows/macOS installers. This
directory has **two independent packaging paths**, targeting the pinned release tag
`v02.07.01.62` on the `fedora-packaging` branch of this fork.

| | `bambu-studio-bin.spec` (recommended) | `bambu-studio.spec` |
|---|---|---|
| What it does | Repackages Bambu's own official Ubuntu 24.04 AppImage into a native RPM | Compiles BambuStudio from source on Fedora |
| Build time | ~2 minutes (no compilation) | 2-4+ hours (deps superbuild) |
| Status | **Builds and runs successfully** — verified end to end | SRPM builds; full deps compile not yet verified |
| Package name | `bambu-studio-bin` (provides `bambu-studio`) | `bambu-studio` |

Start with `bambu-studio-bin.spec` unless you specifically want a from-scratch Fedora compile.

## `bambu-studio-bin.spec` — AppImage repackage (recommended)

Downloads Bambu's official `BambuStudio_ubuntu24.04-v02.07.01.62-*.AppImage`, extracts it with
`--appimage-extract` (no FUSE needed), and installs the extracted `bin/` + `resources/` tree into
`/usr/libexec/bambu-studio/`, with a thin `/usr/bin/bambu-studio` wrapper (mirroring the AppImage's
own `AppRun`) plus a proper desktop file and hicolor icons pulled straight from the AppImage's own
`usr/share/icons/`.

Two real issues were found and fixed while getting this to build clean on Fedora 44:
- The binary carries a dead build-time `RUNPATH` (`/BambuStudio/deps/build/destdir/.../local/lib`)
  that trips Fedora's `check-rpaths` QA check. It's harmless at runtime (the dynamic linker already
  skips it), but was stripped with `patchelf --remove-rpath` in `%install` rather than suppressing
  the check.
- All of BambuStudio's runtime shared-library dependencies (GTK3, WebKitGTK, GStreamer, ICU, ...)
  resolve automatically against Fedora 44's own system libraries — confirmed via `ldd` before ever
  building the RPM. Only the four FFmpeg-family libs Bambu bundles in the AppImage
  (`libavcodec`/`libavutil`/`libswresample`/`libswscale`) ship alongside the binary; everything else
  is picked up by RPM's automatic dependency generator (103 auto-detected `Requires`).

Verified: builds via mock in ~2 minutes, `desktop-file-validate` passes, and the built binary was
extracted and actually launched on a live desktop session — it initializes, and renders its real
first-run SSL-certificate dialog with no crash.

```bash
# stage sources (the AppImage filename embeds a build timestamp not derivable
# from the version alone — get the exact name from the release page if bumping)
mkdir -p /tmp/rpm-sources-bin
curl -L -o /tmp/rpm-sources-bin/BambuStudio_ubuntu24.04-v02.07.01.62-20260616195227.AppImage \
    https://github.com/bambulab/BambuStudio/releases/download/v02.07.01.62/BambuStudio_ubuntu24.04-v02.07.01.62-20260616195227.AppImage
curl -L -o /tmp/rpm-sources-bin/LICENSE \
    https://raw.githubusercontent.com/bambulab/BambuStudio/v02.07.01.62/LICENSE
cp packaging/fedora/bambu-studio-bin.desktop /tmp/rpm-sources-bin/

mock -r packaging/fedora/mock-fedora-44-x86_64-rpmfusion.cfg \
     --buildsrpm --spec packaging/fedora/bambu-studio-bin.spec \
     --sources /tmp/rpm-sources-bin --resultdir /tmp/mock-result

mock -r packaging/fedora/mock-fedora-44-x86_64-rpmfusion.cfg \
     --rebuild /tmp/mock-result/bambu-studio-bin-*.src.rpm --resultdir /tmp/mock-result
```

## `bambu-studio.spec` — from-source compile (stretch goal)

Builds the deps superbuild (OCCT, OpenCV, wxWidgets, Boost, TBB, ...) and BambuStudio itself
directly via `cmake`/`ninja`, mirroring `BuildLinux.sh` from the repo root (that script is the
reference for what the spec's `%build` section does — read it if something here needs updating for
a newer tag).

- `patches/0001-deps-fix-git-apply-directory-flag.patch` — packaging-only fix for
  [bambulab/BambuStudio#4689](https://github.com/bambulab/BambuStudio/issues/4689), a still-open
  upstream bug where `deps/OCCT/OCCT.cmake` and `deps/OpenCV/OpenCV.cmake` compute a `git apply
  --directory <path>` flag that breaks on Fedora with modern git. Applied as `Patch0` in `%prep`,
  not committed to the tracked source, so `Source0` stays a clean snapshot of the upstream tag.
- `mesa-libOSMesa-devel` (upstream's `linux.d/fedora` dependency list) doesn't exist on Fedora 44 —
  Mesa split it into `mesa-compat-libOSMesa-devel`. Already fixed in the spec's `BuildRequires`.

The SRPM builds cleanly. The full deps compile (the expensive, multi-hour part) has **not** been
verified end to end yet — treat this as unfinished. Given `bambu-studio-bin.spec` already provides
a working, verified package, finishing this is optional follow-up work, not a blocker.

```bash
mkdir -p /tmp/rpm-sources
curl -L -o /tmp/rpm-sources/BambuStudio-02.07.01.62.tar.gz \
    https://github.com/SimbaPlayTT/BambuStudio/archive/refs/tags/v02.07.01.62.tar.gz
cp packaging/fedora/patches/0001-deps-fix-git-apply-directory-flag.patch /tmp/rpm-sources/

mock -r packaging/fedora/mock-fedora-44-x86_64-rpmfusion.cfg \
     --buildsrpm --spec packaging/fedora/bambu-studio.spec \
     --sources /tmp/rpm-sources --resultdir /tmp/mock-result

mock -r packaging/fedora/mock-fedora-44-x86_64-rpmfusion.cfg \
     --rebuild /tmp/mock-result/bambu-studio-*.src.rpm --resultdir /tmp/mock-result
```

Budget 2-4 hours of raw compute on a 12-core machine, plus iteration time for whatever else turns
up — Fedora 44 is very new and the deps superbuild pins fairly specific library versions.

### Known risks / things to watch for (from-source path only)

- **OpenVDB ABI mismatch** (seen upstream on Ubuntu 25.04, issue #7759) — possible if a system
  `openvdb-devel` leaks into `find_package` ahead of the deps-built copy. `linux.d/fedora`'s
  package list doesn't install one, so this is unlikely, but if the deps build fails on OpenVDB
  linking, check for a stray system `openvdb-devel`.
- **Bundled dependencies**: this spec statically links Boost, wxWidgets, OCCT, OpenCV, etc. built
  from source rather than using Fedora's system packages — an upstream design choice (see
  `deps/CMakeLists.txt`) needed to pin exact versions. This is fine for a personal COPR but would
  not meet Fedora's official "no bundled libraries" packaging guideline.
- **Future version bumps**: `Patch0` was generated against `v02.07.01.62` specifically. Re-test it
  with `--fuzz=0` against any newer tag before assuming it still applies cleanly.

## One-time setup (needs your sudo password — run these yourself)

```bash
sudo dnf install -y mock rpmdevtools copr-cli
sudo usermod -a -G mock "$(whoami)"
# log out and back in (or `newgrp mock`) for the group change to take effect
```

## Smoke-test a built RPM

```bash
rpm -qlp /tmp/mock-result/bambu-studio*.x86_64.rpm
sudo dnf install /tmp/mock-result/bambu-studio*.x86_64.rpm
ldd "$(which bambu-studio)" | grep "not found"     # should print nothing
desktop-file-validate /usr/share/applications/BambuStudio.desktop
bambu-studio --help                                 # or launch the GUI
```

## Publish to Fedora COPR

Needs a Fedora Account System (FAS) login — separate from GitHub, set up `copr-cli` first (see
[COPR docs](https://docs.pagure.org/copr.copr/user_documentation.html#authentication)).

```bash
copr-cli create bambu-studio --chroot fedora-44-x86_64 \
    --description "BambuStudio (community Fedora build)" \
    --instructions "dnf copr enable SimbaPlayTT/bambu-studio"

# RPM Fusion must be enabled on the COPR-side chroot too, or the builder can't
# resolve x264-devel (from-source path) or gstreamer1-plugin-openh264 (either path):
copr-cli edit-chroot SimbaPlayTT/bambu-studio/fedora-44-x86_64 \
    --repos "https://download1.rpmfusion.org/free/fedora/releases/\$releasever/Everything/\$basearch/os/"

copr-cli build SimbaPlayTT/bambu-studio /tmp/mock-result/bambu-studio-bin-*.src.rpm
```

Once end users have it: `sudo dnf copr enable SimbaPlayTT/bambu-studio && sudo dnf install bambu-studio`.
