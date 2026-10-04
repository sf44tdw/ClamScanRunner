# ClamScan
# clamavを使用したスキャン用スクリプト

1.アーカイブファイルスキャン前提パッケージインストール。
```
yum -y install bzip2-devel
```

2.スクリプトDL
```
cd && git clone https://github.com/sf44tdw/ClamScanRunner.git
cd ClamScanRunner
./initfreshclam.sh
./clamscan_allow_selinux.sh
./registrationtodaily.sh
echo '/dev/' > /etc/clamscan.exclude
echo '/proc/' >> /etc/clamscan.exclude
echo '/sys/' >> /etc/clamscan.exclude
chmod 644 /etc/clamscan.exclude
```

3.隔離用ディレクトリ作成。
```
sesearch -b antivirus_can_scan_system -AC
mkdir -m 700 -p /var/lib/clamav/quarantine
restorecon -Rv /var/lib/clamav/quarantine
ls -ldZ /var/lib/clamav/quarantine
```

