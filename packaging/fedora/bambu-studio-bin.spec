Name:           bambu-studio-bin
Version:        02.07.01.62
Release:        1%{?dist}
Summary:        3D printer slicer for Bambu Lab printers (official prebuilt binary)

License:        AGPL-3.0-only
URL:            https://github.com/bambulab/BambuStudio

# Bambu's own official release asset (built on Ubuntu 24.04) — not built by this
# packaging. The filename embeds a build timestamp that isn't derivable from
# %%{version} alone; when bumping versions, get the exact filename from
# https://github.com/bambulab/BambuStudio/releases/tag/v%{version}
Source0:        https://github.com/bambulab/BambuStudio/releases/download/v%{version}/BambuStudio_ubuntu24.04-v%{version}-20260616195227.AppImage
Source1:        https://raw.githubusercontent.com/bambulab/BambuStudio/v%{version}/LICENSE
Source2:        bambu-studio-bin.desktop

ExclusiveArch:  x86_64

BuildRequires:  desktop-file-utils
BuildRequires:  patchelf

# So `dnf install bambu-studio` (the from-source package name used by
# packaging/fedora/bambu-studio.spec in this same fork) and `dnf install
# bambu-studio-bin` don't fight over /usr/bin/bambu-studio if both are ever
# built into the same repo.
Provides:       bambu-studio = %{version}-%{release}
Conflicts:      bambu-studio

Requires:       hicolor-icon-theme

%description
BambuStudio is a PrusaSlicer-derived slicer for Bambu Lab (and other) 3D
printers, developed by Bambu Lab. Upstream ships no Fedora package or RPM —
only an Ubuntu-built AppImage plus Windows and macOS installers.

This package does NOT compile BambuStudio from source. It repackages Bambu's
own official Ubuntu 24.04 AppImage build into a native RPM with normal Fedora
desktop integration (menu entry, icon, MIME associations) — the same strategy
the community Flathub build uses. All of BambuStudio's runtime library
dependencies (GTK3, WebKitGTK, GStreamer, ...) are satisfied dynamically
against Fedora's own system libraries; only the handful of FFmpeg-family
libraries Bambu bundles in the AppImage are shipped alongside the binary.

A true Fedora-native, source-compiled build is tracked separately in this
fork under packaging/fedora/bambu-studio.spec (package name bambu-studio).

%prep
# No source archive to unpack (Source0 is a self-extracting AppImage, not a
# tarball) — extraction happens in %%build instead of %%autosetup.

%build
install -m755 %{SOURCE0} ./BambuStudio.AppImage
./BambuStudio.AppImage --appimage-extract >/dev/null
test -x squashfs-root/bin/bambu-studio

cat > bambu-studio.wrapper <<'EOF'
#!/bin/bash
DIR=%{_libexecdir}/bambu-studio/bin
export LD_LIBRARY_PATH="$DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
# Upstream's own AppRun sets this too: BambuStudio segfaults on startup on
# systems where locale info isn't what it expects.
export LC_ALL=C
exec "$DIR/bambu-studio" "$@"
EOF

%install
install -d %{buildroot}%{_libexecdir}/bambu-studio
cp -a squashfs-root/bin %{buildroot}%{_libexecdir}/bambu-studio/
cp -a squashfs-root/resources %{buildroot}%{_libexecdir}/bambu-studio/

# Upstream's binary carries a dead build-time RUNPATH
# (/BambuStudio/deps/build/destdir/.../local/lib) that doesn't exist on any
# real system — the dynamic linker already skips it and falls through to
# LD_LIBRARY_PATH (set by our wrapper script) for the bundled FFmpeg libs, and
# to normal system library resolution for everything else. Fedora's
# check-rpaths QA step correctly flags it as broken, so strip it rather than
# suppress the check.
patchelf --remove-rpath %{buildroot}%{_libexecdir}/bambu-studio/bin/bambu-studio

install -Dm755 bambu-studio.wrapper %{buildroot}%{_bindir}/bambu-studio

install -Dm644 %{SOURCE2} %{buildroot}%{_datadir}/applications/BambuStudio.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/BambuStudio.desktop

for size in 32 128 192; do
    install -Dm644 squashfs-root/usr/share/icons/hicolor/${size}x${size}/apps/BambuStudio.png \
        %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/BambuStudio.png
done

cp %{SOURCE1} LICENSE

%files
%license LICENSE
%{_bindir}/bambu-studio
%{_libexecdir}/bambu-studio/
%{_datadir}/applications/BambuStudio.desktop
%{_datadir}/icons/hicolor/*/apps/BambuStudio.png

%changelog
* Tue Jul 21 2026 SimbaPlayTT <simbabackup2@gmail.com> - 02.07.01.62-1
- Initial Fedora repackage of BambuStudio's official Ubuntu 24.04 AppImage.
