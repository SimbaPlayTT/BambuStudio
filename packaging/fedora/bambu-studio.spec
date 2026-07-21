Name:           bambu-studio
Version:        02.07.01.62
Release:        1%{?dist}
Summary:        3D printer slicer for Bambu Lab printers (PrusaSlicer-derived)

License:        AGPL-3.0-only
URL:             https://github.com/SimbaPlayTT/BambuStudio
Source0:        https://github.com/SimbaPlayTT/BambuStudio/archive/refs/tags/v%{version}.tar.gz#/BambuStudio-%{version}.tar.gz
Patch0:         0001-deps-fix-git-apply-directory-flag.patch

# Only builds on 64-bit x86 for now: the deps superbuild's bundled OCCT/OpenCV/
# wxWidgets/Boost/TBB build has not been validated on other arches by this
# packaging (upstream ships x86_64 + arm64 binaries, but arm64 is untested here).
ExclusiveArch:  x86_64

BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  cmake
BuildRequires:  ninja-build
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  gettext
BuildRequires:  git
BuildRequires:  perl
BuildRequires:  perl-FindBin
BuildRequires:  libtool
BuildRequires:  m4
BuildRequires:  texinfo
BuildRequires:  file
BuildRequires:  dbus-devel
BuildRequires:  eglexternalplatform-devel
BuildRequires:  extra-cmake-modules
BuildRequires:  gstreamer1-devel
BuildRequires:  gstreamer1-plugins-base-devel
BuildRequires:  gstreamer1-plugin-openh264
BuildRequires:  gstreamermm-devel
BuildRequires:  gtk3-devel
BuildRequires:  webkit2gtk4.1-devel
BuildRequires:  libmspack-devel
BuildRequires:  libsecret-devel
BuildRequires:  mesa-libGLU-devel
# Renamed on Fedora 44: upstream's linux.d/fedora list says mesa-libOSMesa-devel,
# but Mesa split the classic OSMesa implementation into a separate compat package.
BuildRequires:  mesa-compat-libOSMesa-devel
BuildRequires:  mesa-libGL-devel
BuildRequires:  openssl-devel
BuildRequires:  wayland-devel
BuildRequires:  wayland-protocols-devel
BuildRequires:  libxkbcommon-devel
BuildRequires:  libcurl-devel
BuildRequires:  libquadmath-devel
BuildRequires:  nasm
BuildRequires:  yasm
BuildRequires:  x264-devel
BuildRequires:  bzip2-devel
BuildRequires:  desktop-file-utils

Requires:       hicolor-icon-theme
Recommends:     gstreamer1-plugin-openh264

# This package builds nearly all of its heavy C++ dependencies (Boost, wxWidgets,
# OCCT, OpenCV, TBB, ...) from source and links them statically, rather than using
# Fedora's system packages for them. That's a deliberate upstream choice (see
# deps/CMakeLists.txt) needed to control exact versions across a very large,
# fast-moving dependency set. It's out of step with Fedora's "no bundled libraries"
# guideline for the official repositories, which is why this spec targets a
# personal COPR rather than Fedora proper.

%description
BambuStudio is a PrusaSlicer-derived slicer for Bambu Lab (and other) 3D
printers, developed by Bambu Lab. Upstream ships no Fedora package or RPM —
only an Ubuntu-built AppImage plus Windows and macOS installers. This package
builds BambuStudio natively from source for Fedora.

This build carries one packaging-only patch (see Patch0) working around a
still-open upstream build bug on Fedora: bambulab/BambuStudio#4689.

%prep
%autosetup -p1 -n BambuStudio-%{version}

%build
# NOTE: BambuStudio's build is a two-stage superbuild (deps/ builds ~20 bundled
# C++ dependencies via ExternalProject, then the main app links against them via
# CMAKE_PREFIX_PATH). This doesn't fit the single-tree %%cmake/%%cmake_build
# macros, so %%build calls cmake directly instead, mirroring BuildLinux.sh's own
# `-d` then `-s` steps verbatim (see BuildLinux.sh in this source tree).
%set_build_flags

# --- Dependency superbuild (OCCT, OpenCV, wxWidgets, Boost, TBB, ...) ---
cmake -S deps -B deps/build -G Ninja \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DDEP_WX_GTK3=ON
cmake --build deps/build %{?_smp_mflags}

# --- BambuStudio itself ---
# -DSLIC3R_FHS=1 makes `cmake --install` land files in standard FHS locations
# (see packaging/fedora/README.md for why).
cmake -S . -B build -G Ninja \
    -DCMAKE_PREFIX_PATH="$PWD/deps/build/destdir/usr/local" \
    -DSLIC3R_STATIC=1 \
    -DSLIC3R_GTK=3 \
    -DSLIC3R_FHS=1 \
    -DCMAKE_INSTALL_PREFIX=%{_prefix} \
    -DBBL_RELEASE_TO_PUBLIC=1 \
    -DBBL_INTERNAL_TESTING=0
cmake --build build %{?_smp_mflags} --target BambuStudio

%install
DESTDIR=%{buildroot} cmake --install build

# Not covered by the upstream SLIC3R_FHS install rules (only BambuStudio.desktop
# is installed there) — add the companion gcode-viewer launcher by hand.
install -Dm644 src/platform/unix/BambuGcodeviewer.desktop \
    %{buildroot}%{_datadir}/applications/BambuGcodeviewer.desktop

desktop-file-validate %{buildroot}%{_datadir}/applications/BambuStudio.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/BambuGcodeviewer.desktop

%files
%license LICENSE
%{_bindir}/bambu-studio
%{_bindir}/libavcodec.so.61*
%{_bindir}/libavutil.so.59*
%{_bindir}/libswresample.so.5*
%{_bindir}/libswscale.so.8*
%{_datadir}/applications/BambuStudio.desktop
%{_datadir}/applications/BambuGcodeviewer.desktop
%{_datadir}/icons/hicolor/*/apps/BambuStudio.png
%{_datadir}/BambuStudio/

%changelog
* Tue Jul 21 2026 SimbaPlayTT <simbabackup2@gmail.com> - 02.07.01.62-1
- Initial Fedora packaging of BambuStudio v02.07.01.62.
- Carries a packaging-only patch for upstream issue #4689 (OCCT/OpenCV
  git-apply --directory flag breaks on Fedora with modern git).
