# RTX Graph

RTXルーターのSNMP（IF-MIB）を定期ポーリングし、RRDtoolで時系列保存・PNGグラフ生成を行う、
ISP/IX風のクラシックNOC向けトラフィック監視システムです。

- Python実装 (requires Python 3.11 due to pysnmp compatibility)
- Docker / docker-composeで完結
- 複数ルーター・複数インターフェース対応
- Basic認証付きWeb UI
- 1day / 1week / 1month グラフ生成
- incoming=緑 / outgoing=紫

## 画面イメージ

- Home: `router` 一覧
- Router: `interface` 一覧
- Interface: 1day / 1week / 1month グラフ表示

古典的なNOC/IX運用画面の雰囲気を意識し、シンプルHTML + minimal CSSで構成しています。

## ディレクトリ構成

```
.
├─ app/
│  ├─ main.py          # エントリーポイント
│  ├─ config.py        # config.yaml読み込み
│  ├─ models.py        # SQLite管理
│  ├─ snmp.py          # SNMP polling
│  ├─ rrd.py           # RRD create/update/graph
│  ├─ poller.py        # 1回分のポーリング処理
│  ├─ scheduler.py     # 定期実行
│  ├─ web.py           # Flask + Basic認証
│  └─ utils.py         # パス・文字列ユーティリティ
├─ templates/          # HTMLテンプレート
├─ static/             # CSS
├─ config.yaml         # SNMP対象設定
├─ .env                # Basic認証などの環境変数
├─ Dockerfile
└─ docker-compose.yml
```

## 設定

### `config.yaml`

```yaml
poll_interval: 300

routers:
  - name: rtx-main
    host: 192.0.2.1
    community: public
    version: 2c
    port: 161
    timeout: 2
    retries: 1
    interfaces:
      - if_index: 1
        name: ge0
      - if_index: 2
        name: ge1
```

- `poll_interval`: ポーリング間隔（秒）
- `if_index`: IF-MIBのifIndex
- RTX SNMPは標準IF-MIB（`ifHCInOctets`, `ifHCOutOctets`）前提

### `.env`

```dotenv
WEB_USERNAME=noc
WEB_PASSWORD=change-this-password
WEB_REFRESH_SECONDS=300
```

- 本番では `WEB_PASSWORD` を必ず変更してください。

## 起動方法

1. `config.yaml` を実環境に合わせて編集
2. `.env` の認証情報を変更
3. コンテナ起動

```bash
docker compose up -d --build
```

Web UI: `http://localhost:8080`

## データ保存

`./data` ボリューム配下に保存されます。

- `data/traffic.db` : SQLite
- `data/rrd/` : RRDファイル
- `data/graphs/` : 生成PNG

## 実装ポイント

- SNMP取得は `pysnmp`
- RRDtoolはCLIをPythonから呼び出し
- スケジューラは `asyncio` ベース
- poll失敗時はログ出力し、次サイクル継続（エラー耐性）
- DBにはルーター/インターフェース/ポーリングログを保存

## 注意事項

- 初回ポーリング直後はグラフに十分なデータ点がなく、線が少ない場合があります
- SNMP到達性・community・ifIndexが正しいことを確認してください
- 監視対象が増えた場合は `config.yaml` に追記するだけで拡張可能です