#多重起動防止機講
# 同じ名前のプロセスが起動していたら起動しない。
_lockfile="/tmp/$(basename $0).lock"
ln -s /dummy ${_lockfile} 2>/dev/null || {
	echo 'Cannot run multiple instance.'
	exit 9
}
trap "rm ${_lockfile}; exit" 1 2 3 15

CLAMD_CONFIG_FILE_NAME="/etc/clamd.d/scan.conf"
cp -a ${CLAMD_CONFIG_FILE_NAME}{,.$(date +%Y%m%d%H%M%S).bak} || exit 2
sed -i '/^Example/s/^/#/' ${CLAMD_CONFIG_FILE_NAME}
sed -i 's/^User clamscan/User root/g' ${CLAMD_CONFIG_FILE_NAME}
sed -i 's/^#TCPSocket 3310/TCPSocket 3310/g' ${CLAMD_CONFIG_FILE_NAME}
sed -i 's/^#TCPAddr 127.0.0.1/TCPAddr 127.0.0.1/g' ${CLAMD_CONFIG_FILE_NAME}
sed -i 's/^#LocalSocket \/run\/clamd.scan\/clamd.sock/LocalSocket \/run\/clamd.scan\/clamd.sock/g' ${CLAMD_CONFIG_FILE_NAME}
sed -i '/^#ExcludePath \^\/.*/d' ${CLAMD_CONFIG_FILE_NAME}
sed -i '/^ExcludePath \^\/.*/d' ${CLAMD_CONFIG_FILE_NAME}

echo '' >>"${CLAMD_CONFIG_FILE_NAME}"
echo 'ExcludePath ^/proc/' >>"${CLAMD_CONFIG_FILE_NAME}"
echo 'ExcludePath ^/sys/' >>"${CLAMD_CONFIG_FILE_NAME}"
echo 'ExcludePath ^/dev/' >>"${CLAMD_CONFIG_FILE_NAME}"
echo 'ExcludePath ^/etc/' >>"${CLAMD_CONFIG_FILE_NAME}"
echo 'ExcludePath ^/var/lib/selinux/' >>"${CLAMD_CONFIG_FILE_NAME}"
echo 'ExcludePath ^/var/log/' >>"${CLAMD_CONFIG_FILE_NAME}"
echo 'ExcludePath ^/run/systemd/inaccessible' >>"${CLAMD_CONFIG_FILE_NAME}"

time systemctl enable --now clamd@scan
systemctl restart clamd@scan
systemctl status --no-pager clamd@scan

rm ${_lockfile}
