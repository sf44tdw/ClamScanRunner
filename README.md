# ClamScanRunner

ClamAV でファイルシステム全体を毎日スキャンし、検出したファイルを隔離するスクリプトです。

## RPM のビルドとインストール

RHEL 系の systemd を使用する環境を対象とします。`clamav`、`clamav-update` などの依存パッケージを提供するリポジトリ（必要に応じて EPEL）を有効にしてください。

チェックアウトしたコミットからソースアーカイブを作り、RPM をビルドします。未コミットの変更はアーカイブに含まれません。

```bash
sudo dnf install rpm-build systemd-rpm-macros
mkdir -p ~/rpmbuild/{SOURCES,RPMS}
git archive --format=tar --prefix=clamscanrunner-1.0/ HEAD | gzip > ~/rpmbuild/SOURCES/clamscanrunner-1.0.tar.gz
rpmbuild -ba clamscanrunner.spec
sudo dnf install ~/rpmbuild/RPMS/noarch/clamscanrunner-1.0-2*.noarch.rpm
```

初回インストール時に、RPM は以下を行います。

- `/usr/sbin/clamscanrunner` と `/etc/cron.daily/clamscanrunner` を配置し、`crond` を有効化・起動します。実行時刻はシステムの cron/anacron 設定に依存します。
- `/etc/clamscan.exclude` に `/dev/`、`/proc/`、`/sys/` を設定します。既存の設定は上書きせず、更新時も変更を保持します。
- `/etc/freshclam.conf` をタイムスタンプ付きでバックアップし、`Example` を無効化して `freshclam` を実行します。`NotifyClamd` は自動で有効化せず、既存の設定も変更しません。
- SELinux が有効な場合、`antivirus_can_scan_system` を永続的に有効にします。
- ロックの後始末用 systemd サービスを有効化します。通常のシャットダウン時に `/tmp/clamscanrunner.lock` を削除し、電源断等で削除できなかった場合は次回起動時に tmpfiles が削除します。電源断や強制停止時のシャットダウン処理は保証できません。

初回のウイルス定義更新にはネットワーク接続が必要です。設定、定義更新、サービス起動に失敗しても RPM のインストール自体は完了します。表示された `WARNING` を確認し、必要な操作を手動で再実行してください。コンテナーやオフラインのインストール先など、systemd が稼働していない環境ではサービスの有効化・起動が失敗することがあります。

旧 RPM が有効化した `NotifyClamd /etc/clamd.d/scan.conf` も、更新時には自動変更しません。clamd を使用していない場合は `/etc/freshclam.conf` を確認し、この設定行を手動でコメントアウトしてください。clamd を使用する場合は通知先の設定を維持してください。

ビルド済み RPM のインストール・更新・削除スクリプトを、ホストの設定を変更せずにテストするには以下を実行します。

```bash
CLAMSCANRUNNER_RPM="$HOME/rpmbuild/RPMS/noarch/clamscanrunner-1.0-2.el10.noarch.rpm" python3 tests/test_rpm_scriptlets.py
```

RPM のファイル名はビルド環境のディストリビューションに合わせて変更してください。

## GitHub リリース

GitHub でリリースを公開すると、そのタグのソースから AlmaLinux 10 のコンテナーで RPM をビルドし、テスト後にリリースへ添付します。公開後にワークフローが完了するまで、RPM は表示されません。配布ファイル名は `clamscanrunner-<バージョン>-<リリース番号>.rpm`（例: `clamscanrunner-1.0-2.rpm`）で、パッケージのアーキテクチャは `noarch` です。バージョンとリリース番号はタグ名ではなく spec ファイルに従うため、リリース前に必要に応じて更新してください。同名ファイルがすでにある場合は上書きします。

同じ配布用 RPM をローカルでビルドするには、通常のビルド依存に加えて Git、Python 3、tar、gzip を用意し、コミット済みのソースから以下を実行します。

```bash
bash scripts/build-release-rpm.sh dist
```

従来のスクリプトで登録した既知の再起動用 cron ジョブは初回インストール時に削除します。変更されたジョブは自動削除しないので、警告が表示された場合は `/etc/cron.d/remove_clamscan_runner_lockfile` を確認して削除してください。新旧のロック削除処理を同時に使わないでください。

必要に応じて隔離ディレクトリの SELinux ラベルを復元してください。

```bash
sudo mkdir -m 700 -p /var/lib/clamav/quarantine
sudo restorecon -Rv /var/lib/clamav/quarantine
```

## アンインストール

```bash
sudo dnf remove clamscanrunner
```

毎日の実行設定とロック後始末サービスは削除されます。共有サービスの `crond`、ウイルス定義、ログ、隔離ファイル、`freshclam.conf` とそのバックアップ、および SELinux boolean の変更は削除・復元しません。変更された `/etc/clamscan.exclude` は RPM により `.rpmsave` として保存されます。

## GitHub Actions

`main` ブランチへのプルリクエストでは、追跡対象のシェルスクリプトを `bash -n` で構文チェックします。マージ前にこのチェックを必須にするには、GitHub のブランチ保護ルールで `Shell syntax check / bash -n` を必須ステータスチェックに設定してください。
