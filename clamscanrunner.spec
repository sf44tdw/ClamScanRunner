Name:           clamscanrunner
Version:        1.0
Release:        2%{?dist}
Summary:        Daily ClamAV scan runner
License:        GPL-3.0-or-later
URL:            https://github.com/sf44tdw/ClamScanRunner
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  systemd-rpm-macros
Requires:       bash
Requires:       clamav
Requires:       clamav-update
Requires:       coreutils
Requires:       cronie-anacron
Requires:       findutils
Requires:       grep
Requires:       libselinux-utils
Requires:       policycoreutils
Requires:       policycoreutils-python-utils
Requires:       procps-ng
Requires:       sed
Requires:       systemd

%description
Runs a daily ClamAV scan and moves detected files to a quarantine directory.

%prep
%autosetup

%build

%install
install -Dpm 755 clamscanrunner %{buildroot}%{_sbindir}/clamscanrunner
install -d %{buildroot}%{_sysconfdir}/cron.daily
ln -s %{_sbindir}/clamscanrunner %{buildroot}%{_sysconfdir}/cron.daily/clamscanrunner
install -Dpm 644 clamscan.exclude %{buildroot}%{_sysconfdir}/clamscan.exclude
install -Dpm 644 clamscanrunner-lock-cleanup.service %{buildroot}%{_unitdir}/clamscanrunner-lock-cleanup.service
install -Dpm 644 clamscanrunner.conf %{buildroot}%{_tmpfilesdir}/clamscanrunner.conf

%post
if [ "$1" -eq 1 ]; then
    # Remove the old reboot job only when it matches the former installer.
    old_cron=/etc/cron.d/remove_clamscan_runner_lockfile
    old_helper=/usr/local/bin/remove_clamscan_runner_lockfile
    if [ -f "$old_cron" ] && [ "$(wc -l < "$old_cron")" -eq 2 ] &&
       grep -Fxq 'SHELL=/bin/bash' "$old_cron" &&
       grep -Fxq '@reboot root sleep 60 && /usr/local/bin/remove_clamscan_runner_lockfile clamscanrunner' "$old_cron"; then
        if rm -f "$old_cron"; then
            if [ -f "$old_helper" ] && echo "073b66c562f2bfa46911a5a3f226de7a88a34493edba22375a359fc591810a89  $old_helper" | sha256sum -c --status; then
                rm -f "$old_helper" || echo "WARNING: Could not remove $old_helper" >&2
            fi
        else
            echo "WARNING: Could not remove $old_cron; remove the obsolete reboot job manually." >&2
        fi
    elif [ -e "$old_cron" ]; then
        echo "WARNING: Review $old_cron and remove the obsolete reboot job manually." >&2
    fi

    if cp -a /etc/freshclam.conf "/etc/freshclam.conf.$(date +%%Y%%m%%d%%H%%M%%S).bak"; then
        if sed -i -e '/^Example/s/^/#/' /etc/freshclam.conf; then
            freshclam || echo "WARNING: Initial freshclam update failed; run freshclam manually." >&2
        else
            echo "WARNING: Could not configure /etc/freshclam.conf; configure it and run freshclam manually." >&2
        fi
    else
        echo "WARNING: Could not back up /etc/freshclam.conf; configure it and run freshclam manually." >&2
    fi

    selinux_status=$(getenforce) || selinux_status=unknown
    if [ "$selinux_status" != Disabled ]; then
        semanage boolean -m --on antivirus_can_scan_system || echo "WARNING: Could not enable the antivirus_can_scan_system SELinux boolean." >&2
    fi

    if ! systemctl daemon-reload || ! systemctl enable clamscanrunner-lock-cleanup.service; then
        echo "WARNING: Could not enable lock cleanup; enable clamscanrunner-lock-cleanup.service manually." >&2
    fi
    systemctl enable --now crond.service || echo "WARNING: Could not enable/start crond.service; daily scans will not run until it is started." >&2
fi
exit 0

%preun
if [ "$1" -eq 0 ]; then
    systemctl disable clamscanrunner-lock-cleanup.service || echo "WARNING: Could not disable clamscanrunner-lock-cleanup.service." >&2
fi
exit 0

%postun
systemctl daemon-reload || echo "WARNING: Could not reload systemd after removal or upgrade." >&2
exit 0

%files
%license LICENSE
%doc README.md
%{_sbindir}/clamscanrunner
%{_sysconfdir}/cron.daily/clamscanrunner
%config(noreplace) %{_sysconfdir}/clamscan.exclude
%{_unitdir}/clamscanrunner-lock-cleanup.service
%{_tmpfilesdir}/clamscanrunner.conf

%changelog
* Sun Nov 08 2026 ClamScanRunner contributors - 1.0-2
- Do not enable clamd notification automatically.

* Sun Nov 08 2026 ClamScanRunner contributors - 1.0-1
- Package the daily scanner and lock cleanup.
