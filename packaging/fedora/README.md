# Fedora packaging for BambuStudio

Unofficial, source-compiled Fedora RPM of [BambuStudio](https://github.com/bambulab/BambuStudio).
Upstream ships no Fedora build — only an Ubuntu AppImage, plus Windows/macOS installers. This
directory packages BambuStudio natively for Fedora, built from the pinned release tag
`v02.07.01.62` on the `fedora-packaging` branch of this fork.

## Layout

- `bambu-studio.spec` — the RPM spec. Builds the deps superbuild (OCCT, OpenCV, wxWidgets, Boost,
  TBB, ...) and BambuStudio itself directly via `cmake`/`ninja`, mirroring `BuildLinux.sh` from the
  repo root (that script is the reference for what the spec's `%build` section does — read it if
  something here needs updating for a newer tag).
- `patches/0001-deps-fix-git-apply-directory-flag.patch` — packaging-only fix for
  [bambulab/BambuStudio#4689](https://github.com/bambulab/BambuStudio/issues/4689), a still-open
  upstream bug where `deps/OCCT/OCCT.cmake` and `deps/OpenCV/OpenCV.cmake` compute a `git apply
  --directory <path>` flag that breaks on Fedora with modern git. Applied as `Patch0` in `%prep`,
  not committed to the tracked source, so `Source0` stays a clean snapshot of the upstream tag.
- `mock-fedora-44-x86_64-rpmfusion.cfg` — a `fedora-44-x86_64` mock chroot with RPM Fusion Free
  enabled (required: `x264-devel` and `gstreamer1-plugin-openh264` live there, not in base Fedora).

## One-time setup (needs your sudo password — run these yourself)

```bash
sudo dnf install -y mock rpmdevtools copr-cli
sudo usermod -a -G mock "$(whoami)"
# log out and back in (or `newgrp mock`) for the group change to take effect
```

## Build the SRPM + RPM locally with mock

From the repo root, on the `fedora-packaging` branch:

```bash
# 1. Publish a source tarball for Source0 to fetch. Simplest path: tag+release
#    this branch on your fork and let GitHub generate the tag tarball, since
#    Source0 points at https://github.com/SimbaPlayTT/BambuStudio/archive/refs/tags/v%{version}.tar.gz
git tag v02.07.01.62-fedora1   # or just rely on the existing v02.07.01.62 tag
                                 # from upstream, already present on this fork

# 2. Build SRPM, then full RPM, in the RPM-Fusion-enabled chroot
mock -r packaging/fedora/mock-fedora-44-x86_64-rpmfusion.cfg \
     --buildsrpm --spec packaging/fedora/bambu-studio.spec \
     --sources packaging/fedora/patches --resultdir /tmp/mock-result

mock -r packaging/fedora/mock-fedora-44-x86_64-rpmfusion.cfg \
     --rebuild /tmp/mock-result/bambu-studio-*.src.rpm --resultdir /tmp/mock-result
```

Expect the deps superbuild to dominate build time — budget 2-4 hours of raw compute on a 12-core
machine for one clean build.

## Smoke-test the result

```bash
rpm -qlp /tmp/mock-result/bambu-studio-*.x86_64.rpm
sudo dnf install /tmp/mock-result/bambu-studio-*.x86_64.rpm
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
# resolve x264-devel:
copr-cli edit-chroot SimbaPlayTT/bambu-studio/fedora-44-x86_64 \
    --repos "https://download1.rpmfusion.org/free/fedora/releases/\$releasever/Everything/\$basearch/os/"

copr-cli build SimbaPlayTT/bambu-studio /tmp/mock-result/bambu-studio-*.src.rpm
```

Once end users have it: `sudo dnf copr enable SimbaPlayTT/bambu-studio && sudo dnf install bambu-studio`.

## Known risks / things to watch for

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
